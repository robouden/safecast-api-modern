from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class ImportStatus(str, enum.Enum):
    UNPROCESSED = "unprocessed"
    PROCESSED = "processed"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DONE = "done"
    REJECTED = "rejected"


# Alias for compatibility
BgeigieImportStatus = ImportStatus


class MeasurementImport(Base):
    __tablename__ = "measurement_imports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    description = Column(Text)
    url = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status tracking
    status = Column(Enum(ImportStatus), default=ImportStatus.UNPROCESSED)
    approved = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    rejected_by = Column(String(255))
    rejected_at = Column(DateTime)
    
    # Processing metadata
    measurements_count = Column(Integer, default=0)
    lines_count = Column(Integer, default=0)
    
    # File information
    source = Column(String(255))
    
    # Relationships
    user = relationship("User", back_populates="bgeigie_imports")
    measurements = relationship("Measurement", back_populates="measurement_import")

    def __repr__(self):
        return f"<MeasurementImport(id={self.id}, name='{self.name}', status='{self.status}')>"


class BgeigieImport(MeasurementImport):
    __tablename__ = "bgeigie_imports"

    id = Column(Integer, ForeignKey("measurement_imports.id"), primary_key=True)
    
    # BGeigie-specific fields
    cities = Column(String(255))
    credits = Column(String(255))
    height = Column(String(255))
    orientation = Column(String(255))
    
    # Processing details
    auto_apprv = Column(Boolean, default=False)
    would_auto_approve = Column(Boolean, default=False)
    
    # Contact tracking
    contact_email = Column(String(255))
    contact_name = Column(String(255))
    
    # Additional metadata
    subtype = Column(String(50), default="None")  # None, Drive, Surface, Cosmic
    
    # File processing status
    status_details = Column(Text)  # JSON field for detailed status
    
    # Relationships
    bgeigie_logs = relationship("BgeigieLog", back_populates="bgeigie_import", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BgeigieImport(id={self.id}, cities='{self.cities}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cities": self.cities,
            "credits": self.credits,
            "height": self.height,
            "orientation": self.orientation,
            "subtype": self.subtype,
            "status": self.status.value if self.status else None,
            "approved": self.approved,
            "rejected": self.rejected,
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id,
            "measurements_count": self.measurements_count,
            "lines_count": self.lines_count,
            "auto_apprv": self.auto_apprv,
            "would_auto_approve": self.would_auto_approve,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name
        }
