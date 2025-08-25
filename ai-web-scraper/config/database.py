"""
Database configuration and connection management.

This module handles database connections, session management, and provides
utilities for database operations throughout the application.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from config.settings import get_settings
from src.models.database_models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and connection management."""
    
    def __init__(self):
        self.settings = get_settings()
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        
    @property
    def database_url(self) -> str:
        """Get the database URL for synchronous connections."""
        return (
            f"postgresql://{self.settings.db_user}:{self.settings.db_password}"
            f"@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
        )
    
    @property
    def async_database_url(self) -> str:
        """Get the database URL for asynchronous connections."""
        return (
            f"postgresql+asyncpg://{self.settings.db_user}:{self.settings.db_password}"
            f"@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
        )
    
    def get_engine(self):
        """Get or create the synchronous database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.settings.db_pool_size,
                max_overflow=self.settings.db_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                echo=self.settings.db_echo,
            )
            
            # Add connection event listeners
            self._setup_engine_events(self._engine)
            
        return self._engine
    
    def get_async_engine(self):
        """Get or create the asynchronous database engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.async_database_url,
                poolclass=QueuePool,
                pool_size=self.settings.db_pool_size,
                max_overflow=self.settings.db_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                echo=self.settings.db_echo,
            )
            
        return self._async_engine
    
    def get_session_factory(self):
        """Get or create the synchronous session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory
    
    def get_async_session_factory(self):
        """Get or create the asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.get_async_engine(),
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._async_session_factory
    
    def _setup_engine_events(self, engine):
        """Set up database engine event listeners."""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set database-specific connection parameters."""
            if "postgresql" in str(engine.url):
                # Set PostgreSQL-specific parameters
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET timezone TO 'UTC'")
                    cursor.execute("SET statement_timeout = '30s'")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log database connection checkout."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log database connection checkin."""
            logger.debug("Database connection checked in")
    
    async def create_tables(self):
        """Create all database tables."""
        async_engine = self.get_async_engine()
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all database tables."""
        async_engine = self.get_async_engine()
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
    
    async def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            async_engine = self.get_async_engine()
            async with async_engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def close_connections(self):
        """Close all database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Synchronous database connections closed")
        
        if self._async_engine:
            asyncio.create_task(self._async_engine.dispose())
            logger.info("Asynchronous database connections closed")


# Global database configuration instance
db_config = DatabaseConfig()


def get_db_session() -> Session:
    """
    Get a synchronous database session.
    
    This function is typically used with dependency injection in FastAPI.
    """
    session_factory = db_config.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an asynchronous database session as a context manager.
    
    Usage:
        async with get_async_db_session() as session:
            # Use session here
            pass
    """
    async_session_factory = db_config.get_async_session_factory()
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an asynchronous database session for FastAPI dependency injection.
    
    This function is used with FastAPI's Depends() for automatic session management.
    """
    async with get_async_db_session() as session:
        yield session


class DatabaseHealthCheck:
    """Database health check utilities."""
    
    @staticmethod
    async def check_database_health() -> dict:
        """
        Perform comprehensive database health check.
        
        Returns:
            dict: Health check results with connection status, performance metrics, etc.
        """
        health_status = {
            "database_connected": False,
            "connection_pool_status": {},
            "query_performance": {},
            "error_message": None
        }
        
        try:
            # Check basic connectivity
            health_status["database_connected"] = await db_config.check_connection()
            
            if health_status["database_connected"]:
                # Check connection pool status
                engine = db_config.get_async_engine()
                pool = engine.pool
                
                health_status["connection_pool_status"] = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                # Test query performance
                import time
                start_time = time.time()
                
                async with get_async_db_session() as session:
                    result = await session.execute("SELECT COUNT(*) FROM scraping_jobs")
                    job_count = result.scalar()
                
                query_time = time.time() - start_time
                
                health_status["query_performance"] = {
                    "test_query_time_ms": round(query_time * 1000, 2),
                    "total_jobs": job_count
                }
                
        except Exception as e:
            health_status["error_message"] = str(e)
            logger.error(f"Database health check failed: {e}")
        
        return health_status


class DatabaseMigrationHelper:
    """Helper class for database migrations and schema management."""
    
    @staticmethod
    async def initialize_database():
        """Initialize database with all tables and initial data."""
        try:
            await db_config.create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    @staticmethod
    async def reset_database():
        """Reset database by dropping and recreating all tables."""
        try:
            await db_config.drop_tables()
            await db_config.create_tables()
            logger.info("Database reset successfully")
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            raise
    
    @staticmethod
    async def backup_database(backup_path: str):
        """Create a database backup (placeholder for actual implementation)."""
        # This would typically use pg_dump or similar tools
        logger.info(f"Database backup requested to: {backup_path}")
        # Implementation would depend on specific backup requirements
        pass


# Utility functions for common database operations
async def execute_raw_query(query: str, params: Optional[dict] = None) -> list:
    """
    Execute a raw SQL query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of query results
    """
    async with get_async_db_session() as session:
        result = await session.execute(query, params or {})
        return result.fetchall()


async def get_database_stats() -> dict:
    """
    Get database statistics and metrics.
    
    Returns:
        Dictionary containing database statistics
    """
    stats = {}
    
    try:
        async with get_async_db_session() as session:
            # Get table row counts
            tables = ['scraping_jobs', 'scraped_data', 'job_logs', 'system_metrics']
            
            for table in tables:
                result = await session.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = result.scalar()
            
            # Get database size
            result = await session.execute(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            stats["database_size"] = result.scalar()
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        stats["error"] = str(e)
    
    return stats