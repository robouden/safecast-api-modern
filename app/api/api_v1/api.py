from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, measurements, users, devices, device_stories, bgeigie_imports, ingest

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(measurements.router, prefix="/measurements", tags=["measurements"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(device_stories.router, prefix="/device_stories", tags=["device_stories"])
api_router.include_router(bgeigie_imports.router, prefix="/bgeigie_imports", tags=["bgeigie_imports"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

# Legacy compatibility routes
api_router.include_router(measurements.router, prefix="", tags=["measurements"])  # For /measurements endpoint
