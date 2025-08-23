from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import math

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.device import Device
from app.models.user import User
from app.models.measurement import Measurement
from app.schemas.device import (
    Device as DeviceSchema,
    DeviceWithUser,
    DeviceList,
    DeviceCreate,
    DeviceUpdate,
)
from app.schemas.measurement import MeasurementList

router = APIRouter()


@router.get("/", response_model=DeviceList)
async def list_devices(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    model: Optional[str] = Query(None, description="Filter by model"),
    sensor: Optional[str] = Query(None, description="Filter by sensor"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List devices with optional filtering"""
    
    # Build query with user relationship
    query = select(Device).options(selectinload(Device.user))
    
    # Apply filters
    conditions = []
    if manufacturer:
        conditions.append(Device.manufacturer.ilike(f"%{manufacturer}%"))
    if model:
        conditions.append(Device.model.ilike(f"%{model}%"))
    if sensor:
        conditions.append(Device.sensor.ilike(f"%{sensor}%"))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    devices = result.scalars().all()
    
    # Convert to response format
    device_items = []
    for device in devices:
        device_dict = DeviceSchema.from_orm(device).dict()
        device_dict["user_name"] = device.user.name if device.user else None
        device_items.append(DeviceWithUser(**device_dict))
    
    return DeviceList(
        items=device_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )


@router.get("/{device_id}", response_model=DeviceWithUser)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get device by ID"""
    
    query = select(Device).options(selectinload(Device.user)).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_dict = DeviceSchema.from_orm(device).dict()
    device_dict["user_name"] = device.user.name if device.user else None
    
    return DeviceWithUser(**device_dict)


@router.post("/", response_model=DeviceSchema)
async def create_device(
    device_data: DeviceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or get existing device (get_or_create pattern from Rails)"""
    
    # Check if device already exists
    existing_query = select(Device).where(
        Device.manufacturer == device_data.manufacturer,
        Device.model == device_data.model,
        Device.sensor == device_data.sensor
    )
    
    result = await db.execute(existing_query)
    existing_device = result.scalar_one_or_none()
    
    if existing_device:
        return DeviceSchema.from_orm(existing_device)
    
    # Create new device
    device = Device(
        manufacturer=device_data.manufacturer,
        model=device_data.model,
        sensor=device_data.sensor,
        user_id=current_user.id
    )
    
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    return DeviceSchema.from_orm(device)


@router.get("/{device_id}/measurements", response_model=MeasurementList)
async def get_device_measurements(
    device_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get measurements for a specific device"""
    
    # Verify device exists
    device_query = select(Device).where(Device.id == device_id)
    device_result = await db.execute(device_query)
    if not device_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Build measurements query
    query = select(Measurement).options(
        selectinload(Measurement.device),
        selectinload(Measurement.user)
    ).where(Measurement.device_id == device_id)
    
    # Get total count
    count_query = select(func.count()).where(Measurement.device_id == device_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Measurement.captured_at.desc())
    
    result = await db.execute(query)
    measurements = result.scalars().all()
    
    from app.schemas.measurement import Measurement as MeasurementSchema
    
    return MeasurementList(
        items=[MeasurementSchema.from_orm(m) for m in measurements],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )
