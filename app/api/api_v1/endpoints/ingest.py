from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import csv
import io
from datetime import datetime

from app.core.elasticsearch import get_elasticsearch, ElasticsearchClient
from app.schemas.ingest import IngestQuery, IngestResponse, IngestData

router = APIRouter()

# Device groups matching the original Rails configuration
DEVICE_GROUPS = {
    "central_japan": [
        "safecast:974587752", "safecast:479911182", "safecast:4007513236", 
        "safecast:374304606", "safecast:271575163", "safecast:1162749983"
    ],
    "fukushima": ["safecast:2651380949", "safecast:1875225345"],
    "washington": ["safecast:3937710776", "safecast:3856112813", "safecast:2750599726"],
    "boston": ["safecast:3709008148", "safecast:154534971"],
    "san_jose": ["safecast:129232559"],
    "southern_california": [
        "safecast:872300871", "safecast:4267748403", "safecast:4249659165", 
        "safecast:4177786812", "safecast:3768313999", "safecast:3373827677", 
        "safecast:2670856639", "safecast:230442684", "safecast:2299238163", 
        "safecast:2152053642", "safecast:114699387", "safecast:1094924990", 
        "safecast:1045649384"
    ]
}


@router.get("/", response_model=IngestResponse)
async def get_ingest_data(
    area: Optional[str] = Query(None, description="Device area group"),
    field: Optional[str] = Query(None, description="Sensor field to query"),
    uploaded_after: Optional[str] = Query(None, description="Start date filter"),
    uploaded_before: Optional[str] = Query(None, description="End date filter"),
    format: Optional[str] = Query("json", description="Response format (json/csv)"),
    es: ElasticsearchClient = Depends(get_elasticsearch)
):
    """Get ingest data from Elasticsearch for specific device groups and sensors"""
    
    if not area:
        return IngestResponse(data=[])
    
    if area not in DEVICE_GROUPS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid area. Available areas: {list(DEVICE_GROUPS.keys())}"
        )
    
    if not field:
        raise HTTPException(
            status_code=400,
            detail="Field parameter is required"
        )
    
    # Get device URNs for the specified area
    device_urns = DEVICE_GROUPS[area]
    
    # Query Elasticsearch
    try:
        data = await es.get_device_groups_data(
            device_urns=device_urns,
            field=field,
            after=uploaded_after,
            before=uploaded_before
        )
        
        # Transform data to match original format
        ingest_data = []
        for item in data:
            ingest_data.append(IngestData(
                when_captured=item.get("when_captured"),
                value=item.get("value"),
                device=item.get("device")
            ))
        
        return IngestResponse(data=ingest_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query ingest data: {str(e)}")


@router.get("/csv")
async def get_ingest_data_csv(
    area: Optional[str] = Query(None, description="Device area group"),
    field: Optional[str] = Query(None, description="Sensor field to query"),
    uploaded_after: Optional[str] = Query(None, description="Start date filter"),
    uploaded_before: Optional[str] = Query(None, description="End date filter"),
    es: ElasticsearchClient = Depends(get_elasticsearch)
):
    """Get ingest data as CSV export"""
    
    # Get the data using the same logic as JSON endpoint
    response = await get_ingest_data(area, field, uploaded_after, uploaded_before, "csv", es)
    
    if not response.data:
        raise HTTPException(status_code=404, detail="No data found")
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["when_captured", "value", "device"])
    
    # Write data
    for item in response.data:
        writer.writerow([
            item.when_captured.isoformat() if item.when_captured else "",
            item.value or "",
            item.device or ""
        ])
    
    # Create streaming response
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ingest_data.csv"}
    )


@router.post("/measurements")
async def ingest_measurement(
    measurement_data: Dict[str, Any],
    es: ElasticsearchClient = Depends(get_elasticsearch)
):
    """Ingest a new measurement into Elasticsearch"""
    
    # Validate required fields
    required_fields = ["device_urn", "when_captured"]
    for field in required_fields:
        if field not in measurement_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    # Add service upload timestamp
    measurement_data["service_uploaded"] = datetime.utcnow().isoformat()
    
    # Extract device ID from URN
    if "device_urn" in measurement_data:
        device_urn = measurement_data["device_urn"]
        if ":" in device_urn:
            measurement_data["device"] = device_urn.split(":")[-1]
    
    # Index in Elasticsearch
    success = await es.index_measurement(measurement_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to ingest measurement")
    
    return {"status": "success", "message": "Measurement ingested successfully"}


@router.get("/device/{device_urn}/location")
async def get_device_last_location(
    device_urn: str,
    es: ElasticsearchClient = Depends(get_elasticsearch)
):
    """Get the last known location for a device"""
    
    location = await es.query_last_sensor_location(device_urn)
    
    if not location:
        raise HTTPException(status_code=404, detail="No location data found for device")
    
    return {
        "device_urn": device_urn,
        "location": location,
        "last_updated": datetime.utcnow().isoformat()
    }
