"""
SQLAlchemy ORM models and database setup for Supabase PostgreSQL.
Migrated from SQLite to support cloud-hosted database.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    create_engine, Column, String, Float, Boolean, Text, DateTime, Integer
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from dotenv import load_dotenv

from app.config import settings

# Load environment variables
load_dotenv()

# Get database URL from environment or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to SQLite for local development
    DATABASE_URL = "sqlite:///./structural_intelligence.db"
    print("DATABASE_URL not set, using SQLite: structural_intelligence.db")

# Create SQLAlchemy engine
# Note: check_same_thread only for SQLite
engine_kwargs = {
    "pool_pre_ping": True,  # Enable connection health checks
    "echo": False  # Set to True for SQL debugging
}

# Add SQLite-specific settings
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


# ==================== ORM Models ====================

class Material(Base):
    """Building materials with properties and costs."""
    __tablename__ = "materials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    strength = Column(Float, default=0.0)
    durability = Column(Float, default=0.0)
    cost_per_unit = Column(Float, default=0.0)
    unit = Column(String, default="")
    notes = Column(Text, default="")
    cost_level = Column(String, default="")
    strength_level = Column(String, default="")
    durability_level = Column(String, default="")
    best_use = Column(String, default="")


class StructuralElement(Base):
    """Wall segments with real-world measurements."""
    __tablename__ = "structural_elements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True)
    element_type = Column(String)  # 'exterior' or 'interior'
    length_px = Column(Float)
    real_world_length_m = Column(Float)  # Calculated using scale_factor
    thickness_category = Column(String, default='minor')  # 'major' or 'minor'
    thickness_m = Column(Float, default=0.115)
    has_second_floor = Column(Boolean, default=False)
    
    # Store coordinates as JSON string
    coordinates = Column(Text)  # JSON: {"x1": ..., "y1": ..., "x2": ..., "y2": ...}


class Recommendation(Base):
    """Material recommendations per project element."""
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True)
    element_id = Column(String)  # References wall group (e.g., "exterior_walls")
    material_id = Column(String)
    score = Column(Float)
    llm_explanation = Column(Text)
    total_cost = Column(Float)
    volume_m3 = Column(Float)


class ScaleMetadata(Base):
    """Scaling calibration metadata per project."""
    __tablename__ = "scale_metadata"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True, unique=True)
    scale_factor = Column(Float, nullable=False)  # pixels to meters
    scaling_method = Column(String)  # 'ocr', 'heuristic', 'default'
    is_heuristic_scale = Column(Boolean, default=True)
    confidence = Column(Float, default=0.0)
    aspect_ratio = Column(Float, default=1.0)
    reference_length_px = Column(Float, default=0.0)
    reference_length_m = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProjectMetadata(Base):
    """Project-level metadata for tracking uploads."""
    __tablename__ = "project_metadata"
    
    id = Column(String, primary_key=True)  # UUID
    project_name = Column(String)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    image_width = Column(Integer)
    image_height = Column(Integer)
    total_walls = Column(Integer, default=0)
    has_second_floor = Column(Boolean, default=False)
    total_cost_estimate = Column(Float, default=0.0)


# ==================== Database Utilities ====================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database schema and seed initial data.
    Creates all tables in the Supabase 'public' schema.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Seed materials if table is empty
        db = SessionLocal()
        try:
            material_count = db.query(Material).count()
            
            if material_count == 0:
                # Load materials from JSON
                json_path = settings.materials_path
                if json_path.exists():
                    with open(json_path, encoding="utf-8") as f:
                        data = json.load(f)
                        materials = []
                        for m in data.get("materials", []):
                            material = Material(
                                id=m.get("id", str(uuid.uuid4())),
                                name=m.get("name", "Unknown Material"),
                                strength=m.get("strength", 0.0),
                                durability=m.get("durability", 0.0),
                                cost_per_unit=m.get("cost_per_unit", 0.0),
                                unit=m.get("unit", ""),
                                notes=m.get("notes", ""),
                                cost_level=m.get("cost_level", ""),
                                strength_level=m.get("strength_level", ""),
                                durability_level=m.get("durability_level", ""),
                                best_use=m.get("best_use", "")
                            )
                            materials.append(material)
                        
                        db.bulk_save_objects(materials)
                        db.commit()
                        print(f"Seeded {len(materials)} materials into database")
                else:
                    print(f"WARNING: Materials JSON not found at {json_path}")
            else:
                print(f"Database already contains {material_count} materials")
                        
        except Exception as e:
            print(f"ERROR: Error initializing database: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        print("   Make sure DATABASE_URL is set correctly in .env")
        # Don't raise - allow import to succeed even if DB connection fails


def get_db_legacy():
    """
    Legacy compatibility function for code still using raw SQL.
    Returns a SQLAlchemy session that can be used with execute().
    """
    return SessionLocal()


# ==================== Run initialization ====================

# Initialize database on import (non-blocking)
try:
    init_db()
    print(f"Connected to database successfully")
except Exception as e:
    print(f"WARNING: Database initialization deferred: {e}")
    print("   Database will be initialized on first request")
