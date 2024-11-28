"""Local storage module for bookmark data using SQLite."""
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Create base directory for data storage
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Initialize SQLite database
DATABASE_URL = f"sqlite:///{DATA_DIR}/bookmarks.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Category(Base):
    """Category model for storing bookmark categories."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookmarks = relationship("Bookmark", back_populates="category")

class Bookmark(Base):
    """Bookmark model for storing bookmark data."""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    icon_url = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)  # Store additional metadata as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    last_visited = Column(DateTime, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="bookmarks")

class FolderStructure(Base):
    """Model for storing folder structure."""
    __tablename__ = "folder_structure"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    parent_id = Column(Integer, ForeignKey("folder_structure.id"), nullable=True)
    structure = Column(JSON)  # Store folder hierarchy as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow)

# Create database tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
