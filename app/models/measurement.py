from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from datetime import datetime
import hashlib

from app.core.database import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    height = Column(Float)
    location = Column(Geography("POINT", srid=4326), nullable=False)
    location_name = Column(String(255))
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Device and user relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    measurement_import_id = Column(Integer, ForeignKey("measurement_imports.id"))
    
    # Device metadata
    devicetype_id = Column(Integer)
    sensor_id = Column(Integer)
    channel_id = Column(Integer)
    station_id = Column(Integer)
    
    # Revision tracking
    original_id = Column(Integer, ForeignKey("measurements.id"))
    replaced_by = Column(Integer, ForeignKey("measurements.id"))
    expired_at = Column(DateTime)
    
    # Data integrity
    md5sum = Column(String(32), unique=True, index=True)
    
    # Additional metadata
    surface = Column(String(255))
    radiation = Column(String(255))
    updated_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="measurements")
    device = relationship("Device", back_populates="measurements")
    measurement_import = relationship("MeasurementImport", back_populates="measurements")
    last_updater = relationship("User", foreign_keys=[updated_by])
    
    # Self-referential relationships for revisions
    original = relationship("Measurement", remote_side=[id], foreign_keys=[original_id])
    replacement = relationship("Measurement", remote_side=[id], foreign_keys=[replaced_by])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.md5sum:
            self.set_md5sum()

    def set_md5sum(self):
        """Generate MD5 hash for data integrity"""
        if self.value is not None and self.location is not None and self.captured_at is not None:
            # Extract lat/lng from geography point
            lat = lng = 0.0  # Default values
            if hasattr(self, '_latitude') and hasattr(self, '_longitude'):
                lat, lng = self._latitude, self._longitude
            
            hash_string = f"{self.value}{lat}{lng}{self.captured_at}"
            self.md5sum = hashlib.md5(hash_string.encode()).hexdigest()

    @property
    def latitude(self) -> float:
        """Extract latitude from geography point"""
        if self.location:
            # This would need to be implemented based on the actual geography data
            # For now, return a placeholder
            return getattr(self, '_latitude', 0.0)
        return 0.0

    @property
    def longitude(self) -> float:
        """Extract longitude from geography point"""
        if self.location:
            # This would need to be implemented based on the actual geography data
            # For now, return a placeholder
            return getattr(self, '_longitude', 0.0)
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "value": self.value,
            "unit": self.unit,
            "height": self.height,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "devicetype_id": self.devicetype_id,
            "sensor_id": self.sensor_id,
            "channel_id": self.channel_id,
            "station_id": self.station_id,
            "measurement_import_id": self.measurement_import_id,
            "original_id": self.original_id,
        }
