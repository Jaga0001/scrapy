"""
Database initialization and connection management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.database_models import Base

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///webscraper.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database on import
create_tables()