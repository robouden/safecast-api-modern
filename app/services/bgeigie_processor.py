import csv
import io
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import re
import structlog

from app.models.bgeigie_import import BgeigieImport, ImportStatus
from app.models.bgeigie_log import BgeigieLog
from app.models.measurement import Measurement

logger = structlog.get_logger()


class BgeigieProcessor:
    """Service for processing BGeigie log files"""
    
    # BGeigie log format patterns
    BGEIGIE_HEADER_PATTERN = re.compile(r'^# NEW LOG')
    BGEIGIE_DATA_PATTERN = re.compile(
        r'^\$BNRDD,(\d+),(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z),(\d+),(\d+),(\d+),'
        r'([NSEW\d\.\-]+),([NSEW\d\.\-]+),([AVD]),(\d+\.?\d*),([NSEW]),(\d+\.?\d*),([NSEW]),'
        r'(\d+\.?\d*),([NSEW]),(\d+\.?\d*),([NSEW]),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*)'
    )
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_file(self, bgeigie_import: BgeigieImport, file_content: str) -> Dict[str, int]:
        """
        Process a BGeigie log file and create BgeigieLog entries
        
        Returns:
            Dict with processing statistics
        """
        logger.info(f"Processing BGeigie file for import {bgeigie_import.id}")
        
        lines = file_content.strip().split('\n')
        stats = {
            'total_lines': len(lines),
            'processed_lines': 0,
            'valid_measurements': 0,
            'invalid_lines': 0,
            'errors': []
        }
        
        for line_num, line in enumerate(lines, 1):
            try:
                if self._is_header_line(line):
                    continue
                    
                log_entry = self._parse_bgeigie_line(line, line_num)
                if log_entry:
                    bgeigie_log = await self._create_bgeigie_log(bgeigie_import, log_entry)
                    if bgeigie_log:
                        stats['valid_measurements'] += 1
                
                stats['processed_lines'] += 1
                
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {str(e)}")
                stats['invalid_lines'] += 1
                stats['errors'].append(f"Line {line_num}: {str(e)}")
        
        # Update import statistics
        bgeigie_import.lines_count = stats['total_lines']
        bgeigie_import.measurements_count = stats['valid_measurements']
        bgeigie_import.status = ImportStatus.PROCESSED
        
        await self.db.commit()
        
        logger.info(f"Processed {stats['valid_measurements']} measurements from {stats['total_lines']} lines")
        return stats

    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header/comment line"""
        return line.startswith('#') or line.strip() == ''

    def _parse_bgeigie_line(self, line: str, line_num: int) -> Optional[Dict]:
        """Parse a single BGeigie data line"""
        match = self.BGEIGIE_DATA_PATTERN.match(line.strip())
        if not match:
            return None
        
        try:
            groups = match.groups()
            
            # Parse timestamp
            timestamp_str = groups[1]
            captured_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Parse location
            lat_raw, lng_raw = groups[5], groups[6]
            gps_validity = groups[7]
            
            latitude = self._parse_coordinate(lat_raw, groups[9])
            longitude = self._parse_coordinate(lng_raw, groups[11])
            altitude = float(groups[12]) if groups[12] else None
            
            # Parse sensor data
            cpm = float(groups[2]) if groups[2] else None
            cpm2 = float(groups[3]) if groups[3] else None
            total_count = int(groups[4]) if groups[4] else None
            
            # Additional sensor data (if available)
            temperature = float(groups[16]) if len(groups) > 16 and groups[16] else None
            humidity = float(groups[17]) if len(groups) > 17 and groups[17] else None
            pressure = float(groups[18]) if len(groups) > 18 and groups[18] else None
            battery_voltage = float(groups[15]) if groups[15] else None
            
            return {
                'device_serial_id': groups[0],
                'captured_at': captured_at,
                'cpm': cpm,
                'cpm2': cpm2,
                'total_count': total_count,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'gps_validity': gps_validity,
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'battery_voltage': battery_voltage,
            }
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse line {line_num}: {str(e)}")
            return None

    def _parse_coordinate(self, coord_str: str, direction: str) -> Optional[float]:
        """Parse GPS coordinate from NMEA format"""
        try:
            if not coord_str or coord_str == '0':
                return None
                
            # Handle decimal degrees format
            coord = float(coord_str)
            
            # Apply direction
            if direction in ['S', 'W']:
                coord = -coord
                
            return coord
        except (ValueError, TypeError):
            return None

    async def _create_bgeigie_log(self, bgeigie_import: BgeigieImport, log_data: Dict) -> Optional[BgeigieLog]:
        """Create a BgeigieLog entry from parsed data"""
        try:
            # Create PostGIS point if we have valid coordinates
            location = None
            if log_data['latitude'] and log_data['longitude']:
                point_wkt = f"POINT({log_data['longitude']} {log_data['latitude']})"
                location = text(f"ST_GeogFromText('{point_wkt}')")
            
            bgeigie_log = BgeigieLog(
                bgeigie_import_id=bgeigie_import.id,
                device_serial_id=log_data['device_serial_id'],
                captured_at=log_data['captured_at'],
                cpm=log_data['cpm'],
                cpm2=log_data['cpm2'],
                total_count=log_data['total_count'],
                computed_location=location,
                latitude=log_data['latitude'],
                longitude=log_data['longitude'],
                altitude=log_data['altitude'],
                gps_validity=log_data['gps_validity'],
                temperature=log_data['temperature'],
                humidity=log_data['humidity'],
                pressure=log_data['pressure'],
                battery_voltage=log_data['battery_voltage'],
            )
            
            self.db.add(bgeigie_log)
            return bgeigie_log
            
        except Exception as e:
            logger.error(f"Failed to create BgeigieLog: {str(e)}")
            return None

    async def create_measurements_from_logs(self, bgeigie_import: BgeigieImport) -> int:
        """
        Convert processed BGeigie logs into Measurement records
        
        Returns:
            Number of measurements created
        """
        logger.info(f"Creating measurements from BGeigie import {bgeigie_import.id}")
        
        # Get all logs for this import
        logs_query = text("""
            SELECT * FROM bgeigie_logs 
            WHERE bgeigie_import_id = :import_id 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
            AND cpm IS NOT NULL
        """)
        
        result = await self.db.execute(logs_query, {"import_id": bgeigie_import.id})
        logs = result.fetchall()
        
        measurements_created = 0
        
        for log in logs:
            try:
                # Create PostGIS point
                point_wkt = f"POINT({log.longitude} {log.latitude})"
                
                measurement = Measurement(
                    value=log.cpm,
                    unit='cpm',
                    height=log.altitude,
                    location=text(f"ST_GeogFromText('{point_wkt}')"),
                    captured_at=log.captured_at,
                    user_id=bgeigie_import.user_id,
                    device_id=1,  # Default device - should be configurable
                    measurement_import_id=bgeigie_import.id,
                    _latitude=log.latitude,
                    _longitude=log.longitude
                )
                
                measurement.set_md5sum()
                self.db.add(measurement)
                measurements_created += 1
                
            except Exception as e:
                logger.error(f"Failed to create measurement from log {log.id}: {str(e)}")
        
        # Set original_id for all measurements
        await self.db.flush()
        
        # Update import status
        bgeigie_import.measurements_count = measurements_created
        bgeigie_import.status = ImportStatus.SUBMITTED
        
        await self.db.commit()
        
        logger.info(f"Created {measurements_created} measurements from BGeigie import")
        return measurements_created

    async def approve_import(self, bgeigie_import: BgeigieImport, moderator_name: str) -> bool:
        """Approve a BGeigie import"""
        try:
            bgeigie_import.approved = True
            bgeigie_import.rejected = False
            bgeigie_import.status = ImportStatus.APPROVED
            
            await self.db.commit()
            logger.info(f"BGeigie import {bgeigie_import.id} approved by {moderator_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve import {bgeigie_import.id}: {str(e)}")
            return False

    async def reject_import(self, bgeigie_import: BgeigieImport, moderator_email: str) -> bool:
        """Reject a BGeigie import"""
        try:
            bgeigie_import.approved = False
            bgeigie_import.rejected = True
            bgeigie_import.rejected_by = moderator_email
            bgeigie_import.rejected_at = datetime.utcnow()
            bgeigie_import.status = ImportStatus.REJECTED
            
            await self.db.commit()
            logger.info(f"BGeigie import {bgeigie_import.id} rejected by {moderator_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject import {bgeigie_import.id}: {str(e)}")
            return False
