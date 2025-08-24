from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import structlog

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.elasticsearch import es_client

logger = structlog.get_logger()

templates = Jinja2Templates(directory="app/templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await es_client.create_ingest_template()
    yield
    # Shutdown
    await es_client.close()

app = FastAPI(
    title="Safecast API Modern",
    description="Modern FastAPI implementation of the Safecast radiation monitoring API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Legacy API compatibility - redirect old paths
@app.get("/measurements")
async def legacy_measurements_redirect():
    from fastapi import Request
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/measurements")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    # Get some basic stats for the dashboard
    stats = {
        "total_submissions": "40,338",
        "bgeigie_imports": "1", 
        "pending_approval": "2,524",
        "total_devices": "156"
    }
    
    recent_activity = [
        {
            "type": "Import",
            "description": "New bGeigie log uploaded",
            "date": "2025-08-24 09:30",
            "status": "pending"
        },
        {
            "type": "API",
            "description": "API key generated",
            "date": "2025-08-24 08:15",
            "status": "completed"
        }
    ]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_activity": recent_activity
    })

@app.get("/bgeigie-imports", response_class=HTMLResponse)
async def bgeigie_imports_page(request: Request):
    """bGeigie imports management page"""
    return templates.TemplateResponse("bgeigie_imports.html", {"request": request})

@app.get("/map", response_class=HTMLResponse)
async def map_view(request: Request):
    """Display interactive map with OpenStreetMap showing radiation data"""
    return templates.TemplateResponse("map.html", {"request": request})

@app.get("/measurements", response_class=HTMLResponse)
async def measurements_page(request: Request):
    """Measurements listing page"""
    return templates.TemplateResponse("measurements.html", {"request": request})

@app.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    """Devices listing page"""
    return templates.TemplateResponse("devices.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Users management page"""
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/bgeigie-imports/new", response_class=HTMLResponse)
async def bgeigie_import_new_page(request: Request):
    """New bGeigie import upload page"""
    return templates.TemplateResponse("bgeigie_import_new.html", {"request": request})

@app.get("/bgeigie-imports/{import_id}", response_class=HTMLResponse)
async def bgeigie_import_detail_page(request: Request, import_id: int):
    """bGeigie import detail page"""
    return templates.TemplateResponse("bgeigie_import_detail.html", {
        "request": request,
        "import_id": import_id
    })

@app.get("/safecast-api", response_class=HTMLResponse)
async def safecast_api_page(request: Request):
    """Safecast API information page"""
    return templates.TemplateResponse("safecast_api.html", {"request": request})

@app.get("/device-stories", response_class=HTMLResponse)
async def device_stories_page(request: Request):
    """Device stories page"""
    return templates.TemplateResponse("device_stories.html", {"request": request})

@app.get("/radiation-index", response_class=HTMLResponse)
async def radiation_index_page(request: Request):
    """Radiation index page"""
    return templates.TemplateResponse("radiation_index.html", {"request": request})

@app.get("/ingest-export", response_class=HTMLResponse)
async def ingest_export_page(request: Request):
    """Ingest export page"""
    return templates.TemplateResponse("ingest_export.html", {"request": request})
