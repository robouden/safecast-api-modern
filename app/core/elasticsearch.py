from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class ElasticsearchClient:
    """Elasticsearch client for ingest measurements"""
    
    def __init__(self):
        self.client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            verify_certs=False,
            ssl_show_warn=False
        )
    
    async def close(self):
        """Close the Elasticsearch connection"""
        await self.client.close()
    
    async def create_ingest_template(self):
        """Create the ingest measurements index template"""
        template = {
            "index_patterns": ["ingest-measurements-*"],
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "device_urn": {"type": "keyword"},
                    "device": {"type": "keyword"},
                    "when_captured": {"type": "date"},
                    "service_uploaded": {"type": "date"},
                    "ingest": {
                        "properties": {
                            "location": {
                                "type": "geo_point",
                                "ignore_malformed": True
                            }
                        }
                    },
                    # Air quality sensors
                    "pms_pm01_0": {"type": "float"},
                    "pms_pm02_5": {"type": "float"},
                    "pms_pm10_0": {"type": "float"},
                    # Radiation sensors
                    "lnd_7318u": {"type": "float"},
                    "lnd_7318c": {"type": "float"},
                    # Environmental sensors
                    "env_temp": {"type": "float"},
                    "env_humid": {"type": "float"},
                    "env_press": {"type": "float"},
                    # Device metadata
                    "dev_temp": {"type": "float"},
                    "bat_voltage": {"type": "float"},
                    "bat_current": {"type": "float"},
                    "bat_charge": {"type": "float"}
                }
            }
        }
        
        try:
            await self.client.indices.put_template(
                name="ingest-measurements",
                body=template
            )
            logger.info("Created ingest measurements template")
        except Exception as e:
            logger.error(f"Failed to create ingest template: {str(e)}")
    
    async def index_measurement(self, measurement_data: Dict[str, Any]) -> bool:
        """Index a measurement in Elasticsearch"""
        try:
            # Generate index name based on date
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            index_name = f"ingest-measurements-{date_str}"
            
            # Add timestamp if not present
            if "@timestamp" not in measurement_data:
                measurement_data["@timestamp"] = datetime.utcnow().isoformat()
            
            await self.client.index(
                index=index_name,
                body=measurement_data
            )
            
            logger.debug(f"Indexed measurement to {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index measurement: {str(e)}")
            return False
    
    async def search_measurements(
        self, 
        query: Dict[str, Any], 
        size: int = 100,
        from_: int = 0
    ) -> Dict[str, Any]:
        """Search measurements in Elasticsearch"""
        try:
            response = await self.client.search(
                index="ingest-measurements-*",
                body={
                    "query": query,
                    "size": size,
                    "from": from_,
                    "sort": [{"when_captured": {"order": "desc"}}]
                }
            )
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return {"hits": {"hits": [], "total": {"value": 0}}}
    
    async def get_device_groups_data(
        self, 
        device_urns: List[str], 
        field: str,
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get data for specific device groups"""
        
        query = {
            "bool": {
                "must": [
                    {"terms": {"device_urn": device_urns}}
                ],
                "filter": [
                    {"exists": {"field": field}}
                ]
            }
        }
        
        # Add time range filter
        if after or before:
            time_range = {}
            if after:
                time_range["gte"] = after
            if before:
                time_range["lte"] = before
            
            query["bool"]["must"].append({
                "range": {"when_captured": time_range}
            })
        
        response = await self.search_measurements(query, size=10000)
        
        # Transform response to match original format
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "when_captured": source.get("when_captured"),
                "value": source.get(field),
                "device": source.get("device"),
                **{k: v for k, v in source.items() if k.startswith(field)}
            })
        
        return results
    
    async def query_last_sensor_location(self, device_urn: str) -> Dict[str, Any]:
        """Get the last known location for a device"""
        query = {
            "bool": {
                "must": [
                    {"term": {"device_urn": device_urn}},
                    {"exists": {"field": "ingest.location"}}
                ]
            }
        }
        
        try:
            response = await self.client.search(
                index="ingest-measurements-*",
                body={
                    "query": query,
                    "size": 1,
                    "sort": [{"when_captured": {"order": "desc"}}]
                }
            )
            
            hits = response["hits"]["hits"]
            if hits:
                return hits[0]["_source"].get("ingest", {}).get("location", {})
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get last sensor location: {str(e)}")
            return {}


# Global Elasticsearch client instance
es_client = ElasticsearchClient()


async def get_elasticsearch() -> ElasticsearchClient:
    """Dependency to get Elasticsearch client"""
    return es_client
