from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class DeviceStoryCommentBase(BaseModel):
    content: str = Field(..., max_length=1000, description="Comment content")


class DeviceStoryCommentCreate(DeviceStoryCommentBase):
    pass


class DeviceStoryCommentUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=1000)


class DeviceStoryComment(DeviceStoryCommentBase):
    id: int
    device_story_id: int
    user_id: int
    user_name: Optional[str] = None
    has_image: bool = False
    image_filename: Optional[str] = None
    is_spam: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceStoryBase(BaseModel):
    device_urn: str = Field(..., description="Unique device identifier")
    custodian_name: Optional[str] = None
    last_location_name: Optional[str] = None


class DeviceStoryCreate(DeviceStoryBase):
    pass


class DeviceStoryUpdate(BaseModel):
    custodian_name: Optional[str] = None
    last_location_name: Optional[str] = None


class DeviceStory(DeviceStoryBase):
    id: int
    device_id: Optional[int] = None
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_airnote: bool = False
    comments_count: int = 0

    class Config:
        from_attributes = True


class DeviceStoryWithComments(DeviceStory):
    comments: List[DeviceStoryComment] = []


class DeviceStoryList(BaseModel):
    items: List[DeviceStory]
    total: int
    page: int
    per_page: int
    pages: int


class DeviceStorySearch(BaseModel):
    search: Optional[str] = Field(None, description="Search term for device URN, custodian name, or last seen date")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
