"""
CredentialMD - FastAPI Main Application

Entry point for the FastAPI backend server.
"""

import logging
from contextlib import asynccontextmanager

from config import BACKEND_HOST, BACKEND_PORT, MOCK_MODE, LOG_LEVEL, get_config_summary

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting CredentialMD...")
    logger.info("Configuration: %s", get_config_summary())

    # Initialize database connection
    db.get_connection()

    yield

    # Shutdown
    logger.info("Shutting down CredentialMD...")
    db.close_connection()


# Create FastAPI app
app = FastAPI(
    title="CredentialMD API",
    description="Physician Credentialing Verification Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - returns API info."""
    return {
        "name": "CredentialMD API",
        "version": "0.1.0",
        "mock_mode": MOCK_MODE,
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mock_mode": MOCK_MODE}


@app.get("/api/config")
async def get_config():
    """Get current configuration (for debugging)."""
    return get_config_summary()


# Import and include API routers
from api.routes import router as api_router
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )
