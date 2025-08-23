from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from datetime import datetime
from decimal import Decimal

from app.core.database import Base


class BgeigieLog(Base):
    __tablename__ = "bgeigie_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Raw log data
    device_tag = Column(String(255))
    device_serial_id = Column(String(255))
    captured_at = Column(DateTime)
    cpm = Column(Float)
    cpm2 = Column(Float)
    total_count = Column(Integer)
    
    # Location data
    computed_location = Column(Geography("POINT", srid=4326))
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    gps_validity = Column(String(10))
    
    # Additional sensor data
    temperature = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)
    battery_voltage = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bgeigie_import_id = Column(Integer, ForeignKey("bgeigie_imports.id"), nullable=False)
    bgeigie_import = relationship("BgeigieImport", back_populates="bgeigie_logs")

    @property
    def location(self):
        """Alias for computed_location for compatibility"""
        return self.computed_location

    @location.setter
    def location(self, value):
        """Setter for computed_location"""
        self.computed_location = value

    @property
    def usv(self) -> float:
        """Convert CPM to µSv/h using standard conversion factor"""
        if self.cpm is not None:
            return float(Decimal(str(self.cpm)) / 330)
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "device_tag": self.device_tag,
            "device_serial_id": self.device_serial_id,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "cpm": self.cpm,
            "cpm2": self.cpm2,
            "total_count": self.total_count,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "gps_validity": self.gps_validity,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "battery_voltage": self.battery_voltage,
            "usv": self.usv,
            "bgeigie_import_id": self.bgeigie_import_id,
        }
