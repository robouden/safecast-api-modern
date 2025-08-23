from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from geoalchemy2 import Geometry
from datetime import datetime

from app.core.database import Base


class DeviceStory(Base):
    __tablename__ = "device_stories"

    id = Column(Integer, primary_key=True, index=True)
    device_urn = Column(String(255), unique=True, nullable=False, index=True)
    device_id = Column(Integer)
    custodian_name = Column(String(255))
    last_seen = Column(DateTime)
    last_location = Column(Geometry('POINT'))
    last_location_name = Column(String(255))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = relationship("DeviceStoryComment", back_populates="device_story", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DeviceStory(device_urn='{self.device_urn}', custodian='{self.custodian_name}')>"

    @property
    def is_airnote(self) -> bool:
        """Check if this is an airnote device"""
        return self.device_urn.startswith('note:dev') if self.device_urn else False

    def update_from_metadata(self, metadata: dict):
        """Update device story from TTServe metadata"""
        if 'device' in metadata:
            self.device_id = metadata['device']
        if 'when_captured' in metadata:
            self.last_seen = metadata['when_captured']
        if 'device_contact_name' in metadata:
            self.custodian_name = metadata['device_contact_name']
        
        # Update location if both lon/lat are present
        last_lon = metadata.get('loc_lon')
        last_lat = metadata.get('loc_lat')
        if last_lon and last_lat:
            self.last_location = f"POINT({last_lon} {last_lat})"
            self.last_location_name = metadata.get('location')

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "device_urn": self.device_urn,
            "device_id": self.device_id,
            "custodian_name": self.custodian_name,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_location_name": self.last_location_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_airnote": self.is_airnote,
            "comments_count": len(self.comments) if self.comments else 0,
        }
