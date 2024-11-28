"""Opera bookmark parser implementation."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator
from bs4 import BeautifulSoup, Tag

from parsers.base import BaseBookmarkParser, Bookmark, BookmarkFolder
from utils.chunker import BookmarkChunker

logger = logging.getLogger(__name__)

class OperaBookmarkParser(BaseBookmarkParser):
    """Parser for Opera HTML bookmark files."""

    def __init__(self, max_bookmarks_per_chunk: int = 50):
        """Initialize the Opera bookmark parser.
        
        Args:
            max_bookmarks_per_chunk: Maximum number of bookmarks to process per chunk
        """
        super().__init__("opera")
        self.chunker = BookmarkChunker(max_bookmarks_per_chunk)

    async def parse_file(self, file_path: str) -> AsyncGenerator[BookmarkFolder, None]:
        """Parse an Opera bookmark file in chunks.
        
        Args:
            file_path: Path to the Opera bookmark HTML file
            
        Yields:
            BookmarkFolder: Root folder containing bookmarks for each chunk
            
        Raises:
            FileNotFoundError: If the bookmark file doesn't exist
            ValueError: If the file is not a valid Opera bookmark file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Bookmark file not found: {file_path}")

        async with asyncio.Lock():
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
            
            # Process content in chunks
            for chunk in self.chunker.chunk_content(content):
                folder = await self.parse_content(chunk)
                yield folder

    async def parse_content(self, content: str) -> BookmarkFolder:
        """Parse Opera bookmark HTML content.
        
        Args:
            content: HTML content of the Opera bookmark file
            
        Returns:
            BookmarkFolder: Root folder containing all bookmarks
            
        Raises:
            ValueError: If the content is not valid Opera bookmark HTML
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')
            root_dl = soup.find('dl')
            
            if not root_dl:
                raise ValueError("Not a valid bookmark file: missing root DL element")
            
            def parse_folder(element: Tag) -> Tuple[List[Bookmark], List[BookmarkFolder]]:
                bookmarks = []
                subfolders = []
                
                for dt in element.find_all('dt', recursive=False):
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
                    
                    # Process subfolders
                    h3_tag = dt.find('h3', recursive=False)
                    dl_tag = dt.find('dl', recursive=False)
                    if h3_tag and dl_tag:
                        subfolder_bookmarks, nested_subfolders = parse_folder(dl_tag)
                        subfolders.append(BookmarkFolder(
                            title=h3_tag.get_text(strip=True),
                            bookmarks=subfolder_bookmarks,
                            subfolders=nested_subfolders
                        ))
                
                return bookmarks, subfolders
            
            # Parse the entire bookmark tree
            root_bookmarks, root_subfolders = parse_folder(root_dl)
            
            return BookmarkFolder(
                title="Root",
                bookmarks=root_bookmarks,
                subfolders=root_subfolders
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Opera bookmarks: {str(e)}")
            raise ValueError(f"Failed to parse Opera bookmarks: {str(e)}")
