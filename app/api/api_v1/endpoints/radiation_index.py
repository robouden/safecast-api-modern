from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Query
from enum import Enum
import csv
import os

router = APIRouter()


class RadiationIndexType(str, Enum):
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


@router.get("/radiation_index")
async def get_radiation_index(
    index: RadiationIndexType = Query(RadiationIndexType.AVERAGE, description="Type of radiation index to retrieve")
):
    """Get G20 radiation index data from CSV file"""
    
    # Map enum to CSV row index
    index_mapping = {
        RadiationIndexType.AVERAGE: 0,
        RadiationIndexType.MINIMUM: 1,
        RadiationIndexType.MAXIMUM: 2
    }
    
    try:
        # Read CSV data (in production, this would be in a public directory)
        csv_path = os.path.join("public", "system", "g20.csv")
        
        # For development, create sample data if file doesn't exist
        if not os.path.exists(csv_path):
            return _get_sample_radiation_data(index_mapping[index])
        
        data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(dict(row))
        
        if len(data) <= index_mapping[index]:
            raise HTTPException(status_code=404, detail="Radiation index data not found")
        
        # Get the specified row
        selected_data = data[index_mapping[index]]
        
        # Sort by radiation value (descending), handling None values
        sorted_data = _sort_radiation_data(selected_data)
        
        return {
            "index_type": index.value,
            "data": sorted_data
        }
        
    except FileNotFoundError:
        return _get_sample_radiation_data(index_mapping[index])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading radiation index data: {str(e)}")


def _sort_radiation_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Sort radiation data by value, handling None values"""
    
    # Convert to list of country/value pairs
    country_values = []
    for country, value in data.items():
        if country.lower() in ['index', 'type']:  # Skip metadata columns
            continue
            
        # Handle None/null values
        if value is None or value == '' or value == 'null':
            numeric_value = -1.0
        else:
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                numeric_value = -1.0
        
        country_values.append({
            "country": country,
            "value": round(numeric_value, 1) if numeric_value >= 0 else None,
            "sort_value": numeric_value
        })
    
    # Sort by value (descending)
    country_values.sort(key=lambda x: x["sort_value"], reverse=True)
    
    # Remove sort_value from response
    for item in country_values:
        del item["sort_value"]
    
    return country_values


def _get_sample_radiation_data(index: int) -> Dict[str, Any]:
    """Return sample radiation data for development"""
    
    sample_data = [
        # Average data
        {
            "Japan": 0.15,
            "Germany": 0.08,
            "France": 0.06,
            "United States": 0.12,
            "Canada": 0.09,
            "Australia": 0.07,
            "United Kingdom": 0.05,
            "Italy": 0.10,
            "Spain": 0.08,
            "Brazil": 0.11,
            "Russia": 0.13,
            "China": 0.09,
            "India": 0.14,
            "South Korea": 0.16,
            "Mexico": 0.10,
            "Argentina": 0.08,
            "Turkey": 0.09,
            "Saudi Arabia": 0.07,
            "South Africa": 0.12,
            "Indonesia": 0.08
        },
        # Minimum data
        {
            "Japan": 0.05,
            "Germany": 0.03,
            "France": 0.02,
            "United States": 0.04,
            "Canada": 0.03,
            "Australia": 0.02,
            "United Kingdom": 0.02,
            "Italy": 0.04,
            "Spain": 0.03,
            "Brazil": 0.04,
            "Russia": 0.05,
            "China": 0.03,
            "India": 0.06,
            "South Korea": 0.07,
            "Mexico": 0.04,
            "Argentina": 0.03,
            "Turkey": 0.03,
            "Saudi Arabia": 0.02,
            "South Africa": 0.05,
            "Indonesia": 0.03
        },
        # Maximum data
        {
            "Japan": 0.35,
            "Germany": 0.18,
            "France": 0.15,
            "United States": 0.25,
            "Canada": 0.20,
            "Australia": 0.16,
            "United Kingdom": 0.12,
            "Italy": 0.22,
            "Spain": 0.18,
            "Brazil": 0.24,
            "Russia": 0.28,
            "China": 0.20,
            "India": 0.32,
            "South Korea": 0.38,
            "Mexico": 0.22,
            "Argentina": 0.18,
            "Turkey": 0.20,
            "Saudi Arabia": 0.16,
            "South Africa": 0.26,
            "Indonesia": 0.18
        }
    ]
    
    index_types = ["average", "minimum", "maximum"]
    selected_data = sample_data[index]
    sorted_data = _sort_radiation_data(selected_data)
    
    return {
        "index_type": index_types[index],
        "data": sorted_data,
        "note": "Sample data for development - replace with actual G20 CSV data"
    }
