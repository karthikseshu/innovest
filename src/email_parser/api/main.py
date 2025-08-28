"""
Main FastAPI application for the Email Transaction Parser.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from config.settings import settings
from .routes import router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Reduce noisy loggers from core components to WARNING to keep terminal output concise
_noisy_modules = [
    'src.email_parser.core.email_client',
    'src.email_parser.core.parser_factory',
    'src.email_parser.parsers',
    'src.email_parser.core.transaction_processor'
]
for _m in _noisy_modules:
    logging.getLogger(_m).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="A pluggable utility API for extracting transaction information from emails",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.app_name} v1.0.0")
    logger.info(f"Environment: {settings.log_level}")
    
    # Test connections on startup
    try:
        from ..core.transaction_processor import TransactionProcessor
        processor = TransactionProcessor()
        status = processor.test_connection()
        
        # Database support was removed; only require email connection by default.
        if status.get("email_connection"):
            logger.info("Email connection successful")
            # If a database_connection key still exists (legacy), report it.
            if "database_connection" in status:
                if status.get("database_connection"):
                    logger.info("Database connection successful")
                else:
                    logger.warning("Database connection failed")
            else:
                logger.info("Database connection not configured / skipped")
        else:
            logger.warning("Email connection failed on startup")
            for error in status.get("errors", []):
                logger.warning(f"Connection error: {error}")
    
    except Exception as e:
        logger.error(f"Startup connection test failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.app_name}")


# Include API routes
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Email Transaction Parser API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.email_parser.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
