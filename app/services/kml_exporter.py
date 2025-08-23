from typing import List, Optional
import simplekml
from io import BytesIO
import zipfile
from datetime import datetime

from app.models.bgeigie_import import BgeigieImport
from app.models.bgeigie_log import BgeigieLog


class KMLExporter:
    """Service for exporting BGeigie data to KML/KMZ formats"""
    
    @staticmethod
    def create_kml_from_import(bgeigie_import: BgeigieImport, logs: List[BgeigieLog]) -> str:
        """Create KML content from BGeigie import and logs"""
        
        kml = simplekml.Kml()
        kml.document.name = f"BGeigie Import {bgeigie_import.id}"
        kml.document.description = f"""
        BGeigie Import Data
        File: {bgeigie_import.source_filename or 'Unknown'}
        Uploaded: {bgeigie_import.created_at.strftime('%Y-%m-%d %H:%M:%S') if bgeigie_import.created_at else 'Unknown'}
        Status: {bgeigie_import.status.value if bgeigie_import.status else 'Unknown'}
        Total Logs: {len(logs)}
        """
        
        # Create folder for the import
        folder = kml.newfolder(name=f"Import {bgeigie_import.id}")
        
        # Add logs as placemarks
        for log in logs:
            if log.latitude and log.longitude:
                # Create placemark for each log entry
                placemark = folder.newpoint(
                    name=f"Log {log.id}",
                    coords=[(log.longitude, log.latitude)]
                )
                
                # Add description with measurement data
                description_parts = [
                    f"Captured: {log.captured_at.strftime('%Y-%m-%d %H:%M:%S') if log.captured_at else 'Unknown'}",
                    f"CPM: {log.cpm}" if log.cpm is not None else "",
                    f"Radiation: {log.radiation} µSv/h" if log.radiation is not None else "",
                    f"Temperature: {log.temperature}°C" if log.temperature is not None else "",
                    f"Humidity: {log.humidity}%" if log.humidity is not None else "",
                    f"Pressure: {log.pressure} hPa" if log.pressure is not None else "",
                    f"Altitude: {log.altitude} m" if log.altitude is not None else "",
                ]
                
                placemark.description = "<br/>".join(filter(None, description_parts))
                
                # Style based on radiation level
                if log.radiation is not None:
                    if log.radiation > 1.0:  # High radiation
                        placemark.style.iconstyle.color = simplekml.Color.red
                        placemark.style.iconstyle.scale = 1.2
                    elif log.radiation > 0.5:  # Medium radiation
                        placemark.style.iconstyle.color = simplekml.Color.orange
                        placemark.style.iconstyle.scale = 1.0
                    else:  # Low radiation
                        placemark.style.iconstyle.color = simplekml.Color.green
                        placemark.style.iconstyle.scale = 0.8
        
        # Create path/track if there are multiple points
        if len(logs) > 1:
            # Sort logs by captured time
            sorted_logs = sorted([log for log in logs if log.latitude and log.longitude], 
                               key=lambda x: x.captured_at or datetime.min)
            
            if len(sorted_logs) > 1:
                coords = [(log.longitude, log.latitude) for log in sorted_logs]
                
                linestring = folder.newlinestring(name="Track")
                linestring.coords = coords
                linestring.style.linestyle.color = simplekml.Color.blue
                linestring.style.linestyle.width = 3
                linestring.description = f"BGeigie track with {len(coords)} points"
        
        return kml.kml()
    
    @staticmethod
    def create_kmz_from_import(bgeigie_import: BgeigieImport, logs: List[BgeigieLog]) -> bytes:
        """Create KMZ (compressed KML) content from BGeigie import and logs"""
        
        # Generate KML content
        kml_content = KMLExporter.create_kml_from_import(bgeigie_import, logs)
        
        # Create KMZ (ZIP file with KML)
        kmz_buffer = BytesIO()
        
        with zipfile.ZipFile(kmz_buffer, 'w', zipfile.ZIP_DEFLATED) as kmz:
            # Add KML file to ZIP
            kmz.writestr('doc.kml', kml_content.encode('utf-8'))
            
            # Could add additional files here (icons, overlays, etc.)
        
        kmz_buffer.seek(0)
        return kmz_buffer.getvalue()
    
    @staticmethod
    def get_filename(bgeigie_import: BgeigieImport, format_type: str = 'kml') -> str:
        """Generate appropriate filename for export"""
        
        base_name = f"bgeigie_import_{bgeigie_import.id}"
        
        if bgeigie_import.source_filename:
            # Use original filename base if available
            original_base = bgeigie_import.source_filename.rsplit('.', 1)[0]
            base_name = f"{original_base}_export"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}.{format_type}"
