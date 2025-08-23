from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
import math

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.measurement import Measurement
from app.models.user import User
from app.models.device import Device
from app.schemas.measurement import (
    Measurement as MeasurementSchema,
    MeasurementCreate,
    MeasurementUpdate,
    MeasurementList,
    MeasurementQuery,
)

router = APIRouter()


@router.get("/count")
async def get_measurements_count(
    db: AsyncSession = Depends(get_db),
):
    """Get total count of measurements"""
    
    query = select(func.count(Measurement.id))
    result = await db.execute(query)
    total = result.scalar()
    
    return {"count": total}


@router.get("/", response_model=MeasurementList)
async def get_measurements(
    # Filtering parameters
    unit: Optional[str] = Query(None, description="Filter by unit (e.g., 'cpm', 'usv')"),
    since: Optional[datetime] = Query(None, description="Filter measurements after this date"),
    until: Optional[datetime] = Query(None, description="Filter measurements before this date"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    
    # Spatial filtering
    latitude: Optional[float] = Query(None, description="Center latitude for spatial query"),
    longitude: Optional[float] = Query(None, description="Center longitude for spatial query"),
    distance: Optional[float] = Query(None, description="Distance in km for spatial query"),
    
    # Pagination
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    
    db: AsyncSession = Depends(get_db),
):
    """Get measurements with filtering and pagination"""
    
    # Build base query
    query = select(Measurement).options(
        selectinload(Measurement.device),
        selectinload(Measurement.user)
    )
    
    # Apply filters
    conditions = []
    
    if unit:
        conditions.append(Measurement.unit == unit)
    
    if since:
        conditions.append(Measurement.captured_at >= since)
    
    if until:
        conditions.append(Measurement.captured_at <= until)
    
    if device_id:
        conditions.append(Measurement.device_id == device_id)
    
    if user_id:
        conditions.append(Measurement.user_id == user_id)
    
    # Spatial filtering using PostGIS
    if latitude is not None and longitude is not None and distance is not None:
        # Convert distance from km to meters for PostGIS
        distance_meters = distance * 1000
        point = f"POINT({longitude} {latitude})"
        conditions.append(
            func.ST_DWithin(
                Measurement.location,
                func.ST_GeomFromText(point, 4326),
                distance_meters
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Measurement.captured_at.desc())
    
    result = await db.execute(query)
    measurements = result.scalars().all()
    
    return MeasurementList(
        items=[MeasurementSchema.from_orm(m) for m in measurements],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )


@router.get("/{measurement_id}", response_model=MeasurementSchema)
async def get_measurement(
    measurement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get measurement by ID"""
    
    query = select(Measurement).options(
        selectinload(Measurement.device),
        selectinload(Measurement.user)
    ).where(Measurement.id == measurement_id)
    
    result = await db.execute(query)
    measurement = result.scalar_one_or_none()
    
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    return MeasurementSchema.from_orm(measurement)


@router.post("/", response_model=MeasurementSchema)
async def create_measurement(
    measurement_data: MeasurementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new measurement"""
    
    # Verify device exists and belongs to user
    if measurement_data.device_id:
        device_query = select(Device).where(Device.id == measurement_data.device_id)
        device_result = await db.execute(device_query)
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        if device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Device does not belong to current user")
    
    # Create measurement
    measurement = Measurement(
        value=measurement_data.value,
        unit=measurement_data.unit,
        captured_at=measurement_data.captured_at or datetime.utcnow(),
        location=f"POINT({measurement_data.longitude} {measurement_data.latitude})" if measurement_data.latitude and measurement_data.longitude else None,
        latitude=measurement_data.latitude,
        longitude=measurement_data.longitude,
        device_id=measurement_data.device_id,
        user_id=current_user.id,
        height=measurement_data.height,
        surface=measurement_data.surface,
        radiation=measurement_data.radiation,
        temperature=measurement_data.temperature,
        humidity=measurement_data.humidity,
        pressure=measurement_data.pressure,
    )
    
    db.add(measurement)
    await db.commit()
    await db.refresh(measurement)
    
    # Load relationships
    await db.refresh(measurement, ["device", "user"])
    
    return MeasurementSchema.from_orm(measurement)


@router.put("/{measurement_id}", response_model=MeasurementSchema)
async def update_measurement(
    measurement_id: int,
    measurement_data: MeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a measurement (only by owner or moderator)"""
    
    # Get measurement
    query = select(Measurement).options(
        selectinload(Measurement.device),
        selectinload(Measurement.user)
    ).where(Measurement.id == measurement_id)
    
    result = await db.execute(query)
    measurement = result.scalar_one_or_none()
    
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    # Check permissions
    if measurement.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to update this measurement")
    
    # Update fields
    update_data = measurement_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["latitude", "longitude"] and value is not None:
            setattr(measurement, field, value)
            # Update location if both lat/lon are provided
            if measurement.latitude and measurement.longitude:
                measurement.location = f"POINT({measurement.longitude} {measurement.latitude})"
        else:
            setattr(measurement, field, value)
    
    await db.commit()
    await db.refresh(measurement)
    
    return MeasurementSchema.from_orm(measurement)


@router.delete("/{measurement_id}")
async def delete_measurement(
    measurement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a measurement (only by owner or moderator)"""
    
    # Get measurement
    query = select(Measurement).where(Measurement.id == measurement_id)
    result = await db.execute(query)
    measurement = result.scalar_one_or_none()
    
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    # Check permissions
    if measurement.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to delete this measurement")
    
    await db.delete(measurement)
    await db.commit()
    
    return {"message": "Measurement deleted successfully"}
