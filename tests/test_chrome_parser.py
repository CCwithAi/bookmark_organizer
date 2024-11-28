"""Tests for Chrome bookmark parser."""
import pytest
from datetime import datetime
from pathlib import Path

from src.parsers.chrome import ChromeBookmarkParser


@pytest.fixture
def sample_bookmarks() -> str:
    """Create a sample Chrome bookmarks HTML string."""
    return '''<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'">
<meta content="Bookmarks" name="title">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 ADD_DATE="1635789600" LAST_MODIFIED="1635789600">AI Resources</H3>
    <DL><p>
        <DT><A HREF="https://www.example.com/ai" ADD_DATE="1635789600" ICON="data:image/png;base64,abc">AI Example</A>
        <DT><H3 ADD_DATE="1635789600">Machine Learning</H3>
        <DL><p>
            <DT><A HREF="https://www.example.com/ml" ADD_DATE="1635789600">ML Example</A>
        </DL><p>
    </DL><p>
    <DT><H3 ADD_DATE="1635789600">Development</H3>
    <DL><p>
        <DT><A HREF="https://www.example.com/dev" ADD_DATE="1635789600">Dev Example</A>
    </DL><p>
</DL><p>'''


@pytest.fixture
def parser():
    """Create a ChromeBookmarkParser instance."""
    return ChromeBookmarkParser()


@pytest.mark.asyncio
async def test_parse_content(parser, sample_bookmarks):
    """Test parsing bookmark content."""
    root = await parser.parse_content(sample_bookmarks)
    
    # Check root structure
    assert len(root.subfolders) == 2
    assert root.name == "root"
    
    # Check AI Resources folder
    ai_folder = root.subfolders[0]
    assert ai_folder.name == "AI Resources"
    assert len(ai_folder.bookmarks) == 1
    assert len(ai_folder.subfolders) == 1
    
    # Check AI bookmark
    ai_bookmark = ai_folder.bookmarks[0]
    assert ai_bookmark.url == "https://www.example.com/ai"
    assert ai_bookmark.title == "AI Example"
    assert ai_bookmark.folder_path == ["AI Resources"]
    assert ai_bookmark.icon_url == "data:image/png;base64,abc"
    
    # Check Machine Learning subfolder
    ml_folder = ai_folder.subfolders[0]
    assert ml_folder.name == "Machine Learning"
    assert len(ml_folder.bookmarks) == 1
    
    # Check ML bookmark
    ml_bookmark = ml_folder.bookmarks[0]
    assert ml_bookmark.url == "https://www.example.com/ml"
    assert ml_bookmark.title == "ML Example"
    assert ml_bookmark.folder_path == ["AI Resources", "Machine Learning"]
    
    # Check Development folder
    dev_folder = root.subfolders[1]
    assert dev_folder.name == "Development"
    assert len(dev_folder.bookmarks) == 1
    
    # Check Dev bookmark
    dev_bookmark = dev_folder.bookmarks[0]
    assert dev_bookmark.url == "https://www.example.com/dev"
    assert dev_bookmark.title == "Dev Example"
    assert dev_bookmark.folder_path == ["Development"]


@pytest.mark.asyncio
async def test_invalid_content(parser):
    """Test parsing invalid content."""
    with pytest.raises(ValueError):
        await parser.parse_content("<html><body>Not a bookmark file</body></html>")


@pytest.mark.asyncio
async def test_parse_file_not_found(parser):
    """Test parsing non-existent file."""
    with pytest.raises(FileNotFoundError):
        await parser.parse_file("nonexistent.html")


@pytest.mark.asyncio
async def test_timestamp_parsing(parser):
    """Test parsing Chrome timestamps."""
    # Chrome timestamps are in microseconds since epoch
    timestamp = "1635789600"
    expected_date = datetime.fromtimestamp(int(timestamp))
    parsed_date = parser._parse_date(timestamp)
    assert parsed_date == expected_date
    
    # Test invalid timestamp
    assert parser._parse_date("invalid") is None
    assert parser._parse_date(None) is None
