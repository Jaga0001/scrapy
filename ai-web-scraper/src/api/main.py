"""
FastAPI main application module.

This module contains the main FastAPI application with all routes, middleware,
and configuration for the web scraping API service.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from src.api.routes import jobs, data, health
from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.logging import LoggingMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting FastAPI application")
    
    # Initialize database connections, Redis, etc.
    try:
        # Database initialization would go here
        logger.info("Database connections initialized")
        
        # Redis initialization would go here
        logger.info("Redis connections initialized")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down FastAPI application")
        # Cleanup connections, background tasks, etc.


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Intelligent Web Scraper API",
        description="A comprehensive web scraping API with AI-powered content processing",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    
    # Include routers
    app.include_router(
        health.router,
        prefix="/api/v1/health",
        tags=["Health Check"]
    )
    
    app.include_router(
        jobs.router,
        prefix="/api/v1/scraping",
        tags=["Scraping Jobs"]
    )
    
    app.include_router(
        data.router,
        prefix="/api/v1/data",
        tags=["Scraped Data"]
    )
    
    # Global exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error for {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "message": "The request contains invalid data",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception for {request.url}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="Intelligent Web Scraper API",
            version="1.0.0",
            description="""
            ## Overview
            
            A comprehensive web scraping API that combines Selenium-based web scraping 
            with AI-powered content processing. This API provides endpoints for:
            
            - **Job Management**: Create, monitor, and control scraping jobs
            - **Data Access**: Retrieve and export scraped data with filtering
            - **Health Monitoring**: Check system status and performance metrics
            
            ## Authentication
            
            Most endpoints require JWT authentication. Include the token in the 
            Authorization header: `Bearer <your-token>`
            
            ## Rate Limiting
            
            API requests are rate-limited to prevent abuse:
            - 100 requests per minute for authenticated users
            - 20 requests per minute for unauthenticated users
            
            ## Error Handling
            
            The API uses standard HTTP status codes and returns detailed error 
            information in JSON format.
            """,
            routes=app.routes,
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app


# Create the application instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Intelligent Web Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )