from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class DeviceStoryComment(Base):
    __tablename__ = "device_story_comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    device_story_id = Column(Integer, ForeignKey("device_stories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Image attachment (stored as filename/path)
    image_filename = Column(String(255))
    image_content_type = Column(String(100))
    image_file_size = Column(Integer)
    
    # Spam detection
    is_spam = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device_story = relationship("DeviceStory", back_populates="comments")
    user = relationship("User", back_populates="device_story_comments")

    def __repr__(self):
        return f"<DeviceStoryComment(id={self.id}, device_story_id={self.device_story_id}, user_id={self.user_id})>"

    @property
    def has_image(self) -> bool:
        """Check if comment has an attached image"""
        return bool(self.image_filename)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "content": self.content,
            "device_story_id": self.device_story_id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "has_image": self.has_image,
            "image_filename": self.image_filename,
            "is_spam": self.is_spam,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
