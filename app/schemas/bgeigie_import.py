from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.models.bgeigie_import import ImportStatus


class BgeigieImportBase(BaseModel):
    name: str = Field(..., description="Import name/title")
    description: Optional[str] = Field(None, description="Import description")
    cities: Optional[str] = Field(None, description="Cities covered by this import")
    credits: Optional[str] = Field(None, description="Credits/attribution")
    height: Optional[str] = Field(None, description="Height information")
    orientation: Optional[str] = Field(None, description="Device orientation")


class BgeigieImportCreate(BgeigieImportBase):
    pass


class BgeigieImportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cities: Optional[str] = None
    credits: Optional[str] = None
    height: Optional[str] = None
    orientation: Optional[str] = None


class BgeigieLogResponse(BaseModel):
    id: int
    device_tag: Optional[str]
    device_serial_id: Optional[str]
    captured_at: Optional[datetime]
    cpm: Optional[float]
    cpm2: Optional[float]
    total_count: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]
    gps_validity: Optional[str]
    temperature: Optional[float]
    humidity: Optional[float]
    pressure: Optional[float]
    battery_voltage: Optional[float]
    usv: Optional[float]

    class Config:
        from_attributes = True


class BgeigieImportResponse(BgeigieImportBase):
    id: int
    status: Optional[ImportStatus]
    approved: bool
    rejected: bool
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    user_id: int
    measurements_count: int
    lines_count: int
    auto_apprv: bool
    would_auto_approve: bool
    contact_email: Optional[str]
    contact_name: Optional[str]
    subtype: Optional[str]

    class Config:
        from_attributes = True


class BgeigieImportWithLogs(BgeigieImportResponse):
    bgeigie_logs: List[BgeigieLogResponse] = []


class BgeigieImportList(BaseModel):
    imports: List[BgeigieImportResponse]
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None


class BgeigieImportQuery(BaseModel):
    # Status filters
    status: Optional[ImportStatus] = None
    approved: Optional[bool] = None
    rejected: Optional[bool] = None
    
    # User filters
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    rejected_by: Optional[str] = None
    
    # Temporal filters
    uploaded_after: Optional[datetime] = None
    uploaded_before: Optional[datetime] = None
    
    # Text search
    q: Optional[str] = Field(None, description="Search in name, description, cities, credits")
    
    # Subtype filter
    subtype: Optional[str] = None
    
    # Pagination
    page: Optional[int] = Field(1, ge=1)
    per_page: Optional[int] = Field(25, ge=1, le=100)
    
    # Sorting
    order: Optional[str] = Field(None, description="Sort order")


class FileUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    upload_path: str


class BgeigieImportStats(BaseModel):
    total_imports: int
    pending_approval: int
    approved: int
    rejected: int
    unprocessed: int
