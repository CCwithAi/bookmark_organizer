"""Chrome bookmark parser implementation."""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup

from .base import BaseBookmarkParser, Bookmark, BookmarkFolder


class ChromeBookmarkParser(BaseBookmarkParser):
    """Parser for Chrome HTML bookmark files."""

    def __init__(self):
        """Initialize the Chrome bookmark parser."""
        super().__init__("chrome")

    async def parse_file(self, file_path: str) -> BookmarkFolder:
        """Parse a Chrome bookmark file.
        
        Args:
            file_path: Path to the Chrome bookmark HTML file
            
        Returns:
            BookmarkFolder: Root folder containing all bookmarks
            
        Raises:
            FileNotFoundError: If the bookmark file doesn't exist
            ValueError: If the file is not a valid Chrome bookmark file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Bookmark file not found: {file_path}")

        async with asyncio.Lock():
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
            return await self.parse_content(content)

    async def parse_content(self, content: str) -> BookmarkFolder:
        """Parse Chrome bookmark HTML content.
        
        Args:
            content: HTML content of the Chrome bookmark file
            
        Returns:
            BookmarkFolder: Root folder containing all bookmarks
            
        Raises:
            ValueError: If the content is not valid Chrome bookmark HTML
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')
            root_dl = soup.find('dl')
            
            if not root_dl:
                raise ValueError("Not a valid bookmark file: missing root DL element")
                
            bookmarks = []
            for dt in root_dl.find_all('dt', recursive=True):
                # Process bookmark links
                a_tag = dt.find('a', recursive=False)
                if a_tag and a_tag.get('href'):
                    bookmarks.append(Bookmark(
                        url=a_tag['href'],
                        title=a_tag.get_text(strip=True),
                        add_date=a_tag.get('add_date', ''),
                        last_modified=a_tag.get('last_modified', ''),
                        source_browser=self.browser_name
                    ))
                    
            return BookmarkFolder(
                title="Root",
                bookmarks=bookmarks,
                subfolders=[]
            )
            
        except Exception as e:
            raise ValueError(f"Failed to parse Chrome bookmarks: {str(e)}")

    def _parse_date(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parse Chrome bookmark timestamp to datetime.
        
        Args:
            timestamp: Chrome bookmark timestamp string
            
        Returns:
            datetime or None: Parsed datetime object or None if invalid
        """
        if not timestamp:
            return None
        try:
            # Chrome timestamps are in microseconds since epoch
            return datetime.fromtimestamp(int(timestamp))
        except (ValueError, TypeError):
            return None
