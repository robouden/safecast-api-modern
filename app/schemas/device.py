from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class DeviceBase(BaseModel):
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    sensor: str = Field(..., description="Sensor type")


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sensor: Optional[str] = None


class Device(DeviceBase):
    id: int
    user_id: int
    measurements_count: int = 0
    last_heard_from: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceWithUser(Device):
    user_name: Optional[str] = None


class DeviceList(BaseModel):
    items: List[DeviceWithUser]
    total: int
    page: int
    per_page: int
    pages: int


class DeviceSearch(BaseModel):
    manufacturer: Optional[str] = Field(None, description="Filter by manufacturer")
    model: Optional[str] = Field(None, description="Filter by model")
    sensor: Optional[str] = Field(None, description="Filter by sensor")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
