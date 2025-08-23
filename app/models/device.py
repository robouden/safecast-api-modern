from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    manufacturer = Column(String(255))
    model = Column(String(255))
    sensor = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Counters
    measurements_count = Column(Integer, default=0)
    
    # Additional metadata
    last_heard_from = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="devices")
    measurements = relationship("Measurement", back_populates="device")

    def __repr__(self):
        return f"<Device(id={self.id}, manufacturer='{self.manufacturer}', model='{self.model}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "sensor": self.sensor,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id,
            "measurements_count": self.measurements_count,
            "last_heard_from": self.last_heard_from.isoformat() if self.last_heard_from else None,
        }
