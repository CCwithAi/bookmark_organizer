"""Storage service for handling bookmark data operations."""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from . import database as db

class StorageService:
    """Service for handling bookmark storage operations."""

    def __init__(self, session: Session):
        """Initialize storage service with database session."""
        self.db = session

    async def save_bookmarks(self, bookmarks: List[Dict]) -> List[db.Bookmark]:
        """Save bookmarks to database.
        
        Args:
            bookmarks: List of bookmark dictionaries
            
        Returns:
            List of saved bookmark objects
        """
        saved_bookmarks = []
        for bookmark_data in bookmarks:
            bookmark = db.Bookmark(
                url=bookmark_data["url"],
                title=bookmark_data["title"],
                description=bookmark_data.get("description"),
                icon_url=bookmark_data.get("icon_url"),
                metadata=bookmark_data.get("metadata", {})
            )
            self.db.add(bookmark)
            saved_bookmarks.append(bookmark)
        
        self.db.commit()
        return saved_bookmarks

    async def save_categories(self, categories: Dict[str, List[Dict]]) -> Dict[str, db.Category]:
        """Save categories and their bookmarks.
        
        Args:
            categories: Dictionary mapping category names to lists of bookmarks
            
        Returns:
            Dictionary mapping category names to saved Category objects
        """
        saved_categories = {}
        for category_name, bookmarks in categories.items():
            category = db.Category(name=category_name)
            self.db.add(category)
            self.db.flush()  # Get category ID
            
            for bookmark_data in bookmarks:
                bookmark = db.Bookmark(
                    url=bookmark_data["url"],
                    title=bookmark_data["title"],
                    category_id=category.id,
                    metadata=bookmark_data.get("metadata", {})
                )
                self.db.add(bookmark)
            
            saved_categories[category_name] = category
        
        self.db.commit()
        return saved_categories

    async def save_folder_structure(self, structure: Dict) -> db.FolderStructure:
        """Save folder structure.
        
        Args:
            structure: Dictionary representing folder hierarchy
            
        Returns:
            Saved FolderStructure object
        """
        folder_structure = db.FolderStructure(
            name="root",
            structure=structure,
            last_modified=datetime.utcnow()
        )
        self.db.add(folder_structure)
        self.db.commit()
        return folder_structure

    async def get_all_bookmarks(self) -> List[db.Bookmark]:
        """Get all bookmarks from database."""
        return self.db.query(db.Bookmark).all()

    async def get_bookmarks_by_category(self, category_name: str) -> List[db.Bookmark]:
        """Get bookmarks for a specific category."""
        return (self.db.query(db.Bookmark)
                .join(db.Category)
                .filter(db.Category.name == category_name)
                .all())

    async def get_latest_folder_structure(self) -> Optional[db.FolderStructure]:
        """Get the most recent folder structure."""
        return (self.db.query(db.FolderStructure)
                .order_by(db.FolderStructure.last_modified.desc())
                .first())
