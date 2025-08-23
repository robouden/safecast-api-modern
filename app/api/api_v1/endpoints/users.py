from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import math

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.measurement import Measurement
from app.schemas.user import (
    UserProfile,
    UserPublic,
    UserList,
    UserUpdate,
)
from app.schemas.measurement import MeasurementList

router = APIRouter()


@router.get("/", response_model=UserList)
async def list_users(
    name: Optional[str] = Query(None, description="Search by user name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all confirmed users with optional name filtering"""
    
    # Build query - only confirmed users
    query = select(User).where(User.confirmed_at.is_not(None))
    
    if name:
        search_term = f"%{name.lower()}%"
        query = query.where(func.lower(User.name).like(search_term))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserList(
        items=[UserPublic.from_orm(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile"""
    return UserProfile.from_orm(current_user)


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile"""
    
    # Update fields
    if user_data.name is not None:
        current_user.name = user_data.name
    if user_data.email is not None:
        # Check if email is already taken
        existing_query = select(User).where(
            User.email == user_data.email,
            User.id != current_user.id
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_data.email
    if user_data.time_zone is not None:
        current_user.time_zone = user_data.time_zone
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserProfile.from_orm(current_user)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID (public information only)"""
    
    query = select(User).where(
        User.id == user_id,
        User.confirmed_at.is_not(None)  # Only confirmed users
    )
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserPublic.from_orm(user)


@router.get("/{user_id}/measurements", response_model=MeasurementList)
async def get_user_measurements(
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get measurements by a specific user"""
    
    # Verify user exists and is confirmed
    user_query = select(User).where(
        User.id == user_id,
        User.confirmed_at.is_not(None)
    )
    user_result = await db.execute(user_query)
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build measurements query
    query = select(Measurement).options(
        selectinload(Measurement.device),
        selectinload(Measurement.user)
    ).where(Measurement.user_id == user_id)
    
    # Get total count
    count_query = select(func.count()).where(Measurement.user_id == user_id)
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
