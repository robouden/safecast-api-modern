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
        r'^\$BNRDD,(\d+),(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z),(.+)'
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
            device_serial_id, timestamp_str, rest = match.groups()
            parts = rest.split(',')
            
            # Parse timestamp
            captured_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Initialize default values
            cpm = cpm2 = total_count = None
            latitude = longitude = altitude = None
            gps_validity = 'V'  # Invalid by default
            temperature = humidity = pressure = battery_voltage = None
            
            # Parse based on number of parts - bGeigie logs have variable formats
            if len(parts) >= 6:
                # Try to parse CPM values (can be at different positions)
                try:
                    # Look for numeric values that could be CPM
                    for i, part in enumerate(parts[:5]):
                        if part.replace('.', '').isdigit() and float(part) > 0:
                            if cpm is None:
                                cpm = float(part)
                            elif cpm2 is None and float(part) != cpm:
                                cpm2 = float(part)
                            elif total_count is None:
                                total_count = int(float(part))
                except (ValueError, IndexError):
                    pass
                
                # Parse GPS data - look for coordinate patterns
                for i in range(len(parts) - 1):
                    try:
                        # Look for latitude/longitude pairs
                        if (i < len(parts) - 3 and 
                            parts[i+1] in ['N', 'S'] and 
                            parts[i+3] in ['E', 'W']):
                            # NMEA format: value, direction, value, direction
                            latitude = self._parse_coordinate(parts[i], parts[i+1])
                            longitude = self._parse_coordinate(parts[i+2], parts[i+3])
                            if i+4 < len(parts):
                                try:
                                    altitude = float(parts[i+4])
                                except ValueError:
                                    pass
                            if i+5 < len(parts):
                                gps_validity = parts[i+5] if parts[i+5] in ['A', 'V'] else 'V'
                            break
                        elif (i < len(parts) - 1 and 
                              self._is_decimal_coordinate(parts[i]) and 
                              self._is_decimal_coordinate(parts[i+1])):
                            # Decimal degrees format
                            latitude = float(parts[i])
                            longitude = float(parts[i+1])
                            if i+2 < len(parts):
                                try:
                                    altitude = float(parts[i+2])
                                except ValueError:
                                    pass
                            gps_validity = 'A'  # Assume valid if we have decimal coordinates
                            break
                    except (ValueError, IndexError):
                        continue
                
                # Parse additional sensor data from end of line
                try:
                    # Look for temperature, humidity, pressure in last few fields
                    if len(parts) >= 3:
                        # Try to parse last few numeric values as sensor data
                        for i in range(max(0, len(parts) - 5), len(parts)):
                            part = parts[i].replace('*', '').split('*')[0]  # Remove checksum
                            if self._is_float(part):
                                val = float(part)
                                if 0 <= val <= 100 and temperature is None:  # Likely temperature
                                    temperature = val
                                elif 0 <= val <= 100 and humidity is None:  # Likely humidity
                                    humidity = val
                                elif 900 <= val <= 1100 and pressure is None:  # Likely pressure
                                    pressure = val
                                elif 0 <= val <= 20 and battery_voltage is None:  # Likely battery
                                    battery_voltage = val
                except (ValueError, IndexError):
                    pass
            
            return {
                'device_serial_id': device_serial_id,
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
            
            # Convert NMEA format (DDMM.MMMM) to decimal degrees if needed
            if coord > 180:  # Likely NMEA format
                degrees = int(coord / 100)
                minutes = coord - (degrees * 100)
                coord = degrees + (minutes / 60)
            
            # Apply direction
            if direction in ['S', 'W']:
                coord = -coord
                
            return coord
        except (ValueError, TypeError):
            return None

    def _is_decimal_coordinate(self, value: str) -> bool:
        """Check if value looks like a decimal coordinate"""
        try:
            coord = float(value)
            return -180 <= coord <= 180
        except (ValueError, TypeError):
            return False

    def _is_float(self, value: str) -> bool:
        """Check if value can be converted to float"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

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
