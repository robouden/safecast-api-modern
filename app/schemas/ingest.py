from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class IngestData(BaseModel):
    when_captured: Optional[datetime] = Field(None, description="When the measurement was captured")
    value: Optional[float] = Field(None, description="Sensor value")
    device: Optional[str] = Field(None, description="Device identifier")


class IngestResponse(BaseModel):
    data: List[IngestData] = Field(default_factory=list, description="List of ingest measurements")


class IngestQuery(BaseModel):
    area: Optional[str] = Field(None, description="Device area group")
    field: Optional[str] = Field(None, description="Sensor field to query")
    uploaded_after: Optional[str] = Field(None, description="Start date filter")
    uploaded_before: Optional[str] = Field(None, description="End date filter")


class IngestMeasurement(BaseModel):
    device_urn: str = Field(..., description="Device URN (e.g., safecast:123456)")
    device: Optional[str] = Field(None, description="Device ID extracted from URN")
    when_captured: datetime = Field(..., description="Measurement timestamp")
    service_uploaded: Optional[datetime] = Field(None, description="Service upload timestamp")
    
    # Location data
    ingest: Optional[Dict[str, Any]] = Field(None, description="Ingest metadata including location")
    
    # Air quality sensors
    pms_pm01_0: Optional[float] = Field(None, description="PM1.0 particulate matter")
    pms_pm02_5: Optional[float] = Field(None, description="PM2.5 particulate matter")
    pms_pm10_0: Optional[float] = Field(None, description="PM10 particulate matter")
    
    # Radiation sensors
    lnd_7318u: Optional[float] = Field(None, description="LND 7318U radiation sensor")
    lnd_7318c: Optional[float] = Field(None, description="LND 7318C radiation sensor")
    
    # Environmental sensors
    env_temp: Optional[float] = Field(None, description="Environmental temperature")
    env_humid: Optional[float] = Field(None, description="Environmental humidity")
    env_press: Optional[float] = Field(None, description="Environmental pressure")
    
    # Device metadata
    dev_temp: Optional[float] = Field(None, description="Device temperature")
    bat_voltage: Optional[float] = Field(None, description="Battery voltage")
    bat_current: Optional[float] = Field(None, description="Battery current")
    bat_charge: Optional[float] = Field(None, description="Battery charge level")


class DeviceLocation(BaseModel):
    device_urn: str
    location: Dict[str, Any]
    last_updated: datetime
