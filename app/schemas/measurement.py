from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class MeasurementBase(BaseModel):
    value: float = Field(..., description="Measurement value")
    unit: str = Field(..., description="Unit of measurement (e.g., 'cpm', 'µSv/h')")
    height: Optional[float] = Field(None, description="Height above ground in meters")
    location_name: Optional[str] = Field(None, description="Human-readable location name")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    captured_at: datetime = Field(..., description="When the measurement was captured")
    
    # Device metadata
    devicetype_id: Optional[int] = Field(None, description="Device type identifier")
    sensor_id: Optional[int] = Field(None, description="Sensor identifier")
    channel_id: Optional[int] = Field(None, description="Channel identifier")
    station_id: Optional[int] = Field(None, description="Station identifier")
    
    # Additional metadata
    surface: Optional[str] = Field(None, description="Surface type")
    radiation: Optional[str] = Field(None, description="Radiation type")

    @validator('unit')
    def validate_unit(cls, v):
        allowed_units = ['cpm', 'µSv/h', 'uSv/h', 'mR/hr', 'nSv/h']
        if v not in allowed_units:
            raise ValueError(f'Unit must be one of: {", ".join(allowed_units)}')
        return v


class MeasurementCreate(MeasurementBase):
    device_id: int = Field(..., description="Device ID that recorded this measurement")


class MeasurementUpdate(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    height: Optional[float] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    captured_at: Optional[datetime] = None
    devicetype_id: Optional[int] = None
    sensor_id: Optional[int] = None
    channel_id: Optional[int] = None
    station_id: Optional[int] = None
    surface: Optional[str] = None
    radiation: Optional[str] = None


class MeasurementResponse(MeasurementBase):
    id: int
    user_id: int
    device_id: int
    measurement_import_id: Optional[int] = None
    original_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeasurementList(BaseModel):
    measurements: list[MeasurementResponse]
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None


class MeasurementQuery(BaseModel):
    # Spatial filters
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    distance: Optional[float] = Field(None, gt=0, description="Distance in kilometers")
    
    # Temporal filters
    captured_after: Optional[datetime] = None
    captured_before: Optional[datetime] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    
    # Data filters
    unit: Optional[str] = None
    device_id: Optional[int] = None
    user_id: Optional[int] = None
    measurement_import_id: Optional[int] = None
    devicetype_id: Optional[int] = None
    sensor_id: Optional[int] = None
    channel_id: Optional[int] = None
    station_id: Optional[int] = None
    original_id: Optional[int] = None
    
    # Pagination
    page: Optional[int] = Field(1, ge=1)
    per_page: Optional[int] = Field(100, ge=1, le=1000)
    limit: Optional[int] = Field(None, ge=1, le=10000)
    
    # Sorting
    order: Optional[str] = Field(None, description="Sort order (e.g., 'captured_at DESC')")


class MeasurementCount(BaseModel):
    count: int = Field(..., description="Total number of measurements")


# Alias for compatibility
Measurement = MeasurementResponse
