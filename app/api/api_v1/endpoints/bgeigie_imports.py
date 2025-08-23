from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional, List
import os
import aiofiles
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.models.bgeigie_import import BgeigieImport, ImportStatus
from app.models.bgeigie_log import BgeigieLog
from app.models.user import User
from app.schemas.bgeigie_import import (
    BgeigieImportResponse,
    BgeigieImportCreate,
    BgeigieImportUpdate,
    BgeigieImportList,
    BgeigieImportWithLogs,
    BgeigieImportQuery,
    BgeigieImportStats,
    FileUploadResponse
)
from app.api.deps import get_current_user, get_current_moderator
from app.services.bgeigie_processor import BgeigieProcessor

router = APIRouter()


@router.get("/", response_model=BgeigieImportList)
async def get_bgeigie_imports(
    # Status filters
    status: Optional[ImportStatus] = None,
    approved: Optional[bool] = None,
    rejected: Optional[bool] = None,
    
    # User filters
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    rejected_by: Optional[str] = None,
    
    # Temporal filters
    uploaded_after: Optional[str] = None,
    uploaded_before: Optional[str] = None,
    
    # Text search
    q: Optional[str] = None,
    
    # Subtype filter
    subtype: Optional[str] = None,
    
    # Pagination
    page: int = 1,
    per_page: int = 25,
    
    # Sorting
    order: Optional[str] = None,
    
    db: AsyncSession = Depends(get_db)
):
    """Get BGeigie imports with filtering and pagination"""
    
    query = select(BgeigieImport).options(selectinload(BgeigieImport.user))
    
    # Apply filters
    if status:
        query = query.where(BgeigieImport.status == status)
    if approved is not None:
        query = query.where(BgeigieImport.approved == approved)
    if rejected is not None:
        query = query.where(BgeigieImport.rejected == rejected)
    if user_id:
        query = query.where(BgeigieImport.user_id == user_id)
    if rejected_by:
        query = query.where(BgeigieImport.rejected_by.ilike(f"%{rejected_by}%"))
    
    # Temporal filters
    if uploaded_after:
        query = query.where(BgeigieImport.created_at > uploaded_after)
    if uploaded_before:
        query = query.where(BgeigieImport.created_at < uploaded_before)
    
    # Text search across multiple fields
    if q:
        search_term = f"%{q.lower()}%"
        query = query.where(
            BgeigieImport.name.ilike(search_term) |
            BgeigieImport.description.ilike(search_term) |
            BgeigieImport.cities.ilike(search_term) |
            BgeigieImport.credits.ilike(search_term)
        )
    
    if subtype:
        query = query.where(BgeigieImport.subtype == subtype)
    
    # Sorting
    if order:
        if order.lower().endswith(' desc'):
            field = order[:-5].strip()
            if hasattr(BgeigieImport, field):
                query = query.order_by(desc(getattr(BgeigieImport, field)))
        elif order.lower().endswith(' asc'):
            field = order[:-4].strip()
            if hasattr(BgeigieImport, field):
                query = query.order_by(asc(getattr(BgeigieImport, field)))
    else:
        query = query.order_by(desc(BgeigieImport.created_at))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    imports = result.scalars().all()
    
    return BgeigieImportList(
        imports=[imp.to_dict() for imp in imports],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/stats", response_model=BgeigieImportStats)
async def get_bgeigie_import_stats(db: AsyncSession = Depends(get_db)):
    """Get BGeigie import statistics"""
    
    total_query = select(func.count(BgeigieImport.id))
    pending_query = select(func.count(BgeigieImport.id)).where(
        BgeigieImport.approved == False,
        BgeigieImport.rejected == False
    )
    approved_query = select(func.count(BgeigieImport.id)).where(BgeigieImport.approved == True)
    rejected_query = select(func.count(BgeigieImport.id)).where(BgeigieImport.rejected == True)
    unprocessed_query = select(func.count(BgeigieImport.id)).where(
        BgeigieImport.status == ImportStatus.UNPROCESSED
    )
    
    total = (await db.execute(total_query)).scalar()
    pending = (await db.execute(pending_query)).scalar()
    approved = (await db.execute(approved_query)).scalar()
    rejected = (await db.execute(rejected_query)).scalar()
    unprocessed = (await db.execute(unprocessed_query)).scalar()
    
    return BgeigieImportStats(
        total_imports=total,
        pending_approval=pending,
        approved=approved,
        rejected=rejected,
        unprocessed=unprocessed
    )


@router.get("/{import_id}", response_model=BgeigieImportWithLogs)
async def get_bgeigie_import(
    import_id: int,
    include_logs: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific BGeigie import by ID"""
    
    query = select(BgeigieImport).options(selectinload(BgeigieImport.user))
    
    if include_logs:
        query = query.options(selectinload(BgeigieImport.bgeigie_logs))
    
    query = query.where(BgeigieImport.id == import_id)
    
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    response_data = bgeigie_import.to_dict()
    
    if include_logs:
        response_data["bgeigie_logs"] = [log.to_dict() for log in bgeigie_import.bgeigie_logs]
    
    return response_data


@router.post("/upload", response_model=BgeigieImportResponse, status_code=201)
async def upload_bgeigie_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a BGeigie log file for processing"""
    
    # Validate file type
    if not file.filename.endswith(('.log', '.txt')):
        raise HTTPException(
            status_code=400,
            detail="Only .log and .txt files are supported"
        )
    
    # Check file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR) / "bgeigie_imports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_path = upload_dir / f"{current_user.id}_{file.filename}"
    
    # Save file
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create BGeigie import record
    bgeigie_import = BgeigieImport(
        name=name,
        description=description,
        source=str(file_path),
        user_id=current_user.id,
        status=ImportStatus.UNPROCESSED
    )
    
    db.add(bgeigie_import)
    await db.commit()
    await db.refresh(bgeigie_import)
    
    # Process file asynchronously (in a real app, this would be a background task)
    try:
        processor = BgeigieProcessor(db)
        file_content = content.decode('utf-8')
        await processor.process_file(bgeigie_import, file_content)
    except Exception as e:
        # If processing fails, mark import as failed but don't delete it
        bgeigie_import.status = ImportStatus.UNPROCESSED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    
    return bgeigie_import.to_dict()


@router.put("/{import_id}", response_model=BgeigieImportResponse)
async def update_bgeigie_import(
    import_id: int,
    import_data: BgeigieImportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a BGeigie import"""
    
    query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    if bgeigie_import.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this import")
    
    # Update fields
    update_data = import_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bgeigie_import, field, value)
    
    await db.commit()
    await db.refresh(bgeigie_import)
    
    return bgeigie_import.to_dict()


@router.patch("/{import_id}/submit", response_model=BgeigieImportResponse)
async def submit_bgeigie_import(
    import_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a BGeigie import for moderation"""
    
    query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    if bgeigie_import.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this import")
    
    if bgeigie_import.status != ImportStatus.PROCESSED:
        raise HTTPException(status_code=400, detail="Import must be processed before submission")
    
    # Validate required fields
    if not bgeigie_import.cities or not bgeigie_import.credits:
        raise HTTPException(
            status_code=400,
            detail="Cities and credits are required before submission"
        )
    
    # Create measurements from logs
    processor = BgeigieProcessor(db)
    measurements_created = await processor.create_measurements_from_logs(bgeigie_import)
    
    bgeigie_import.status = ImportStatus.SUBMITTED
    await db.commit()
    
    return bgeigie_import.to_dict()


@router.patch("/{import_id}/approve", response_model=BgeigieImportResponse)
async def approve_bgeigie_import(
    import_id: int,
    moderator: User = Depends(get_current_moderator),
    db: AsyncSession = Depends(get_db)
):
    """Approve a BGeigie import (moderator only)"""
    
    query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    if bgeigie_import.status != ImportStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Import must be submitted before approval")
    
    processor = BgeigieProcessor(db)
    success = await processor.approve_import(bgeigie_import, moderator.name or moderator.email)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to approve import")
    
    return bgeigie_import.to_dict()


@router.patch("/{import_id}/reject", response_model=BgeigieImportResponse)
async def reject_bgeigie_import(
    import_id: int,
    moderator: User = Depends(get_current_moderator),
    db: AsyncSession = Depends(get_db)
):
    """Reject a BGeigie import (moderator only)"""
    
    query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    processor = BgeigieProcessor(db)
    success = await processor.reject_import(bgeigie_import, moderator.email)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reject import")
    
    return bgeigie_import.to_dict()


@router.get("/{import_id}/logs", response_model=List[dict])
async def get_bgeigie_logs(
    import_id: int,
    page: int = 1,
    per_page: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get BGeigie logs for a specific import"""
    
    # Verify import exists
    import_query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    import_result = await db.execute(import_query)
    if not import_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    # Get logs with pagination
    offset = (page - 1) * per_page
    logs_query = select(BgeigieLog).where(
        BgeigieLog.bgeigie_import_id == import_id
    ).offset(offset).limit(per_page).order_by(BgeigieLog.captured_at)
    
    result = await db.execute(logs_query)
    logs = result.scalars().all()
    
    return [log.to_dict() for log in logs]


@router.delete("/{import_id}", status_code=204)
async def delete_bgeigie_import(
    import_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a BGeigie import"""
    
    query = select(BgeigieImport).where(BgeigieImport.id == import_id)
    result = await db.execute(query)
    bgeigie_import = result.scalar_one_or_none()
    
    if not bgeigie_import:
        raise HTTPException(status_code=404, detail="BGeigie import not found")
    
    if bgeigie_import.user_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to delete this import")
    
    # Delete associated file
    if bgeigie_import.source and os.path.exists(bgeigie_import.source):
        try:
            os.remove(bgeigie_import.source)
        except Exception:
            pass  # File deletion failure shouldn't prevent DB deletion
    
    await db.delete(bgeigie_import)
    await db.commit()
