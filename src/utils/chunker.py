"""Utility for chunking large bookmark files."""
import logging
from bs4 import BeautifulSoup, Tag
from typing import Generator, List, Optional

logger = logging.getLogger(__name__)

class BookmarkChunker:
    """Handles chunking of large bookmark files into manageable pieces."""
    
    def __init__(self, max_bookmarks_per_chunk: int = 50):
        """Initialize the chunker.
        
        Args:
            max_bookmarks_per_chunk: Maximum number of bookmarks per chunk
        """
        self.max_bookmarks_per_chunk = max_bookmarks_per_chunk

    def chunk_content(self, content: str) -> Generator[str, None, None]:
        """Split bookmark content into chunks while preserving structure.
        
        Args:
            content: Full HTML content of the bookmark file
            
        Yields:
            str: HTML content for each chunk with proper structure
        """
        soup = BeautifulSoup(content, "html.parser")
        root_dl = soup.find("dl")
        
        if not root_dl:
            logger.warning("No root DL element found")
            return

        # Get all DT elements containing bookmarks or folders
        all_dt = root_dl.find_all("dt", recursive=True)
        
        # Initialize chunk variables
        current_chunk_dts: List[Tag] = []
        current_bookmark_count = 0
        
        for dt in all_dt:
            # Check if this is a bookmark (has an A tag) or folder (has an H3 tag)
            is_bookmark = dt.find("a") is not None
            
            if is_bookmark:
                current_bookmark_count += 1
            
            current_chunk_dts.append(dt)
            
            # If we've reached the max bookmarks per chunk, yield the chunk
            if current_bookmark_count >= self.max_bookmarks_per_chunk:
                yield self._create_chunk_html(current_chunk_dts)
                current_chunk_dts = []
                current_bookmark_count = 0
        
        # Yield any remaining bookmarks
        if current_chunk_dts:
            yield self._create_chunk_html(current_chunk_dts)

    def _create_chunk_html(self, dt_elements: List[Tag]) -> str:
        """Create a valid HTML bookmark file structure for a chunk.
        
        Args:
            dt_elements: List of DT elements to include in the chunk
            
        Returns:
            str: Valid HTML bookmark file content for the chunk
        """
        # Create a new soup for the chunk
        chunk_soup = BeautifulSoup(
            """<!DOCTYPE NETSCAPE-Bookmark-file-1>
            <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
            <TITLE>Bookmarks</TITLE>
            <H1>Bookmarks</H1>
            <DL><p>
            </DL>""",
            "html.parser"
        )
        
        # Get the root DL element
        chunk_dl = chunk_soup.find("dl")
        
        # Add each DT element to the chunk
        for dt in dt_elements:
            # Create a new copy of the DT to avoid modifying the original
            new_dt = BeautifulSoup(str(dt), "html.parser").dt
            chunk_dl.append(new_dt)
        
        return str(chunk_soup)
