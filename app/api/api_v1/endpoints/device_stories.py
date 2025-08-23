from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, String
from sqlalchemy.orm import selectinload
import math

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.device_story import DeviceStory
from app.models.device_story_comment import DeviceStoryComment
from app.models.user import User
from app.schemas.device_story import (
    DeviceStory as DeviceStorySchema,
    DeviceStoryWithComments,
    DeviceStoryList,
    DeviceStoryComment as DeviceStoryCommentSchema,
    DeviceStoryCommentCreate,
    DeviceStoryCommentUpdate,
)

router = APIRouter()


@router.get("/", response_model=DeviceStoryList)
async def list_device_stories(
    search: Optional[str] = Query(None, description="Search device URN, custodian name, or last seen"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List device stories with optional search"""
    
    # Build query
    query = select(DeviceStory)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(DeviceStory.device_urn).like(search_term),
                func.lower(DeviceStory.custodian_name).like(search_term),
                func.cast(DeviceStory.last_seen, String).like(search_term)
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    device_stories = result.scalars().all()
    
    return DeviceStoryList(
        items=[DeviceStorySchema.from_orm(ds) for ds in device_stories],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )


@router.get("/{device_story_id}", response_model=DeviceStoryWithComments)
async def get_device_story(
    device_story_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get device story by ID with comments"""
    
    query = select(DeviceStory).options(
        selectinload(DeviceStory.comments).selectinload(DeviceStoryComment.user)
    ).where(DeviceStory.id == device_story_id)
    
    result = await db.execute(query)
    device_story = result.scalar_one_or_none()
    
    if not device_story:
        raise HTTPException(status_code=404, detail="Device story not found")
    
    return DeviceStoryWithComments.from_orm(device_story)


@router.get("/airnote/{device_urn}", response_model=DeviceStoryWithComments)
async def get_device_story_by_urn(
    device_urn: str,
    db: AsyncSession = Depends(get_db),
):
    """Get device story by device URN (for airnote compatibility)"""
    
    query = select(DeviceStory).options(
        selectinload(DeviceStory.comments).selectinload(DeviceStoryComment.user)
    ).where(DeviceStory.device_urn == device_urn)
    
    result = await db.execute(query)
    device_story = result.scalar_one_or_none()
    
    if not device_story:
        raise HTTPException(status_code=404, detail="Device story not found")
    
    return DeviceStoryWithComments.from_orm(device_story)


@router.get("/{device_story_id}/comments", response_model=List[DeviceStoryCommentSchema])
async def list_device_story_comments(
    device_story_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List comments for a device story"""
    
    # Verify device story exists
    story_query = select(DeviceStory).where(DeviceStory.id == device_story_id)
    story_result = await db.execute(story_query)
    if not story_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Device story not found")
    
    # Get comments
    query = select(DeviceStoryComment).options(
        selectinload(DeviceStoryComment.user)
    ).where(DeviceStoryComment.device_story_id == device_story_id)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    return [DeviceStoryCommentSchema.from_orm(comment) for comment in comments]


@router.post("/{device_story_id}/comments", response_model=DeviceStoryCommentSchema)
async def create_device_story_comment(
    device_story_id: int,
    comment_data: DeviceStoryCommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new comment on a device story"""
    
    # Verify device story exists
    story_query = select(DeviceStory).where(DeviceStory.id == device_story_id)
    story_result = await db.execute(story_query)
    if not story_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Device story not found")
    
    # Create comment
    comment = DeviceStoryComment(
        content=comment_data.content,
        device_story_id=device_story_id,
        user_id=current_user.id
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    # Load user relationship
    await db.refresh(comment, ["user"])
    
    return DeviceStoryCommentSchema.from_orm(comment)


@router.put("/{device_story_id}/comments/{comment_id}", response_model=DeviceStoryCommentSchema)
async def update_device_story_comment(
    device_story_id: int,
    comment_id: int,
    comment_data: DeviceStoryCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a device story comment"""
    
    # Get comment
    query = select(DeviceStoryComment).options(
        selectinload(DeviceStoryComment.user)
    ).where(
        DeviceStoryComment.id == comment_id,
        DeviceStoryComment.device_story_id == device_story_id
    )
    
    result = await db.execute(query)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions (owner or moderator)
    if comment.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    # Update comment
    if comment_data.content is not None:
        comment.content = comment_data.content
    
    await db.commit()
    await db.refresh(comment)
    
    return DeviceStoryCommentSchema.from_orm(comment)


@router.delete("/{device_story_id}/comments/{comment_id}")
async def delete_device_story_comment(
    device_story_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a device story comment"""
    
    # Get comment
    query = select(DeviceStoryComment).where(
        DeviceStoryComment.id == comment_id,
        DeviceStoryComment.device_story_id == device_story_id
    )
    
    result = await db.execute(query)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions (owner or moderator)
    if comment.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    await db.delete(comment)
    await db.commit()
    
    return {"message": "Comment deleted successfully"}


@router.post("/{device_story_id}/comments/{comment_id}/image")
async def upload_comment_image(
    device_story_id: int,
    comment_id: int,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image for a device story comment"""
    
    # Get comment
    query = select(DeviceStoryComment).where(
        DeviceStoryComment.id == comment_id,
        DeviceStoryComment.device_story_id == device_story_id
    )
    
    result = await db.execute(query)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions
    if comment.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to upload image for this comment")
    
    # Validate image
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    if image.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    # Save image (simplified - in production, use cloud storage)
    import os
    import uuid
    
    upload_dir = "uploads/device_story_comments"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as f:
        content = await image.read()
        f.write(content)
    
    # Update comment
    comment.image_filename = filename
    comment.image_content_type = image.content_type
    comment.image_file_size = len(content)
    
    await db.commit()
    
    return {"message": "Image uploaded successfully", "filename": filename}
