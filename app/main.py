from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.elasticsearch import es_client
from app.api.api_v1.api import api_router


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

@app.get("/")
async def root():
    return {
        "message": "Safecast API Modern",
        "version": "1.0.0",
        "docs": "/docs",
        "legacy_compatibility": True
    }
