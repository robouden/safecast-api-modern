from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    authentication_token = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime)
    confirmation_sent_at = Column(DateTime)
    
    # Profile information
    time_zone = Column(String(255))
    moderator = Column(Boolean, default=False)
    
    # Counters (denormalized for performance)
    measurements_count = Column(Integer, default=0)
    
    # Additional fields from original
    reset_password_token = Column(String(255))
    reset_password_sent_at = Column(DateTime)
    remember_created_at = Column(DateTime)
    sign_in_count = Column(Integer, default=0)
    current_sign_in_at = Column(DateTime)
    last_sign_in_at = Column(DateTime)
    current_sign_in_ip = Column(String(255))
    last_sign_in_ip = Column(String(255))
    confirmation_token = Column(String(255))
    unconfirmed_email = Column(String(255))

    # Relationships
    measurements = relationship("Measurement", foreign_keys="Measurement.user_id", back_populates="user")
    devices = relationship("Device", back_populates="user")
    bgeigie_imports = relationship("BgeigieImport", back_populates="user")
    device_story_comments = relationship("DeviceStoryComment", back_populates="user")

    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"

    @property
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.confirmed_at is not None

    @property
    def is_moderator(self) -> bool:
        """Check if user has moderator privileges"""
        return self.moderator or False

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "measurements_count": self.measurements_count,
            "moderator": self.moderator,
        }
