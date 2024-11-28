"""Base parser for browser bookmarks."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, AsyncGenerator

class Bookmark:
    """Base class for bookmarks."""
    def __init__(self, url: str, title: str, add_date: str = "", last_modified: str = "", source_browser: str = "unknown"):
        self.url = url
        self.title = title
        self.add_date = add_date
        self.last_modified = last_modified
        self.source_browser = source_browser

    def to_dict(self) -> Dict[str, Any]:
        """Convert bookmark to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "add_date": self.add_date,
            "last_modified": self.last_modified,
            "source_browser": self.source_browser
        }


class BookmarkFolder:
    """Base class for bookmark folders."""
    def __init__(self, title: str, bookmarks: List[Bookmark], subfolders: List['BookmarkFolder']):
        self.title = title
        self.bookmarks = [b.to_dict() if isinstance(b, Bookmark) else b for b in bookmarks]
        self.subfolders = subfolders


class BaseBookmarkParser(ABC):
    """Abstract base class for browser bookmark parsers."""

    def __init__(self, browser_name: str):
        """Initialize the parser.
        
        Args:
            browser_name: Name of the browser (e.g., 'chrome', 'edge', 'opera')
        """
        self.browser_name = browser_name

    @abstractmethod
    async def parse_file(self, file_path: str) -> BookmarkFolder:
        """Parse a bookmark file and return a BookmarkFolder object.
        
        Args:
            file_path: Path to the bookmark file
            
        Returns:
            BookmarkFolder: Root folder containing all bookmarks
        """
        pass

    @abstractmethod
    async def parse_content(self, content: str) -> BookmarkFolder:
        """Parse bookmark content string and return a BookmarkFolder object.
        
        Args:
            content: String content of the bookmark file
            
        Returns:
            BookmarkFolder: Root folder containing all bookmarks
        """
        pass

    def _create_bookmark(
        self,
        url: str,
        title: str,
        folder_path: List[str],
        added_date: Optional[datetime] = None,
        last_modified: Optional[datetime] = None,
        icon_url: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Bookmark:
        """Create a Bookmark object with the given parameters.
        
        Args:
            url: The bookmark URL
            title: The bookmark title
            folder_path: List of folder names representing the path to the bookmark
            added_date: When the bookmark was added
            last_modified: When the bookmark was last modified
            icon_url: URL to the bookmark's icon
            description: Description of the bookmark
            tags: List of tags associated with the bookmark
            
        Returns:
            Bookmark: A new Bookmark object
        """
        return Bookmark(
            url=url,
            title=title,
            add_date=added_date.isoformat() if added_date else "",
            last_modified=last_modified.isoformat() if last_modified else "",
            source_browser=self.browser_name,
        )

    def _create_folder(
        self,
        name: str,
        parent_path: Optional[List[str]] = None,
        added_date: Optional[datetime] = None,
        last_modified: Optional[datetime] = None,
    ) -> BookmarkFolder:
        """Create a bookmark folder.
        
        Args:
            name: Folder name
            parent_path: Path to parent folder
            added_date: Date folder was added
            last_modified: Date folder was last modified
            
        Returns:
            BookmarkFolder: Created folder
        """
        return BookmarkFolder(
            title=name,
            bookmarks=[],
            subfolders=[],
        )
