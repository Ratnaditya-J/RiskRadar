"""
Database configuration and management for RiskRadar.
"""

import os
from typing import Optional
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://riskradar:riskradar@localhost:5432/riskradar"
)

# For development, fall back to SQLite if PostgreSQL is not available
SQLITE_URL = "sqlite:///./riskradar.db"

Base = declarative_base()

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Setup database engine and session factory."""
        try:
            # Try PostgreSQL first
            if self.database_url.startswith("postgresql"):
                self.engine = create_engine(self.database_url)
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Connected to PostgreSQL database")
            else:
                raise Exception("PostgreSQL not available")
                
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            logger.info("Falling back to SQLite for development")
            
            # Fall back to SQLite
            self.database_url = SQLITE_URL
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all database tables."""
        from .models import Base
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

# Expose SessionLocal at module level for imports
SessionLocal = db_manager.SessionLocal

def get_db() -> Session:
    """Dependency for getting database sessions."""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database with tables and default data."""
    logger.info("Initializing RiskRadar database...")
    
    # Create tables
    db_manager.create_tables()
    
    # Insert default sources
    from .models import DataSourceORM
    from ..config.default_sources import get_default_sources
    
    db = db_manager.get_session()
    try:
        # Check if sources already exist
        existing_sources = db.query(DataSourceORM).count()
        
        if existing_sources == 0:
            logger.info("Inserting default sources...")
            
            for source_config in get_default_sources():
                source = DataSourceORM(
                    name=source_config["name"],
                    source_type=source_config["source_type"].value,
                    url_pattern=source_config["url_pattern"],
                    keywords=source_config["keywords"],
                    scraping_config=source_config["scraping_config"],
                    rate_limit=source_config["scraping_config"].get("rate_limit", 60),
                    enabled=source_config["enabled"]
                )
                db.add(source)
            
            db.commit()
            logger.info(f"Inserted {len(get_default_sources())} default sources")
        else:
            logger.info(f"Database already contains {existing_sources} sources")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Database health check
def check_database_health() -> bool:
    """Check if database is healthy and accessible."""
    try:
        db = db_manager.get_session()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
