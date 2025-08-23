from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    time_zone: Optional[str] = None


class UserProfile(UserBase):
    id: int
    created_at: Optional[datetime] = None
    measurements_count: int = 0
    moderator: bool = False
    time_zone: Optional[str] = None
    confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: int
    name: Optional[str] = None
    measurements_count: int = 0

    class Config:
        from_attributes = True


class UserList(BaseModel):
    items: List[UserPublic]
    total: int
    page: int
    per_page: int
    pages: int


class UserSearch(BaseModel):
    name: Optional[str] = Field(None, description="Search by user name")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
