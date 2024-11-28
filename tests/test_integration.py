import pytest
import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.backend.app import app
from fastapi.testclient import TestClient
import warnings

# Suppress HTTPX deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx._client")

# Initialize test client
client = TestClient(app)

def test_app_initialization():
    """Test that the FastAPI app is properly initialized."""
    response = client.get("/")
    assert response.status_code in (200, 404)  # Either is acceptable for root endpoint

@pytest.fixture
def chrome_bookmark_content():
    """Sample Chrome bookmark HTML content for testing."""
    return """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <TITLE>Bookmarks</TITLE>
    <H1>Bookmarks</H1>
    <DL><p>
        <DT><H3>Programming</H3>
        <DL><p>
            <DT><A HREF="https://python.org">Python</A>
            <DT><A HREF="https://docs.python.org">Python Docs</A>
        </DL><p>
        <DT><H3>News</H3>
        <DL><p>
            <DT><A HREF="https://news.ycombinator.com">Hacker News</A>
        </DL><p>
    </DL><p>"""

@pytest.fixture
def opera_bookmark_content():
    """Sample Opera bookmark HTML content for testing."""
    return """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <TITLE>OPERA BOOKMARKS</TITLE>
    <H1>Bookmarks</H1>
    <DL><p>
        <DT><H3>Programming</H3>
        <DL><p>
            <DT><A HREF="https://python.org">Python</A>
            <DT><A HREF="https://docs.python.org">Python Docs</A>
        </DL><p>
        <DT><H3>News</H3>
        <DL><p>
            <DT><A HREF="https://news.ycombinator.com">Hacker News</A>
        </DL><p>
    </DL><p>"""

def test_import_chrome_bookmarks(chrome_bookmark_content, tmp_path):
    """Test importing Chrome bookmarks."""
    # Create a temporary bookmark file
    bookmark_file = tmp_path / "bookmarks.html"
    bookmark_file.write_text(chrome_bookmark_content)
    
    # Send the file to the import endpoint
    with open(bookmark_file, "rb") as f:
        response = client.post(
            "/api/import-bookmarks",
            files={"file": ("bookmarks.html", f, "text/html")}
        )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "bookmarks" in data["data"]
    bookmarks = data["data"]["bookmarks"]
    assert len(bookmarks) > 0
    
    # Verify bookmark structure
    urls = [b["url"] for b in bookmarks]
    assert "https://python.org" in urls
    assert "https://docs.python.org" in urls
    assert "https://news.ycombinator.com" in urls

def test_import_opera_bookmarks(opera_bookmark_content, tmp_path):
    """Test importing Opera bookmarks."""
    # Create a temporary bookmark file
    bookmark_file = tmp_path / "bookmarks.html"
    bookmark_file.write_text(opera_bookmark_content)
    
    # Send the file to the import endpoint
    with open(bookmark_file, "rb") as f:
        response = client.post(
            "/api/import-bookmarks",
            files={"file": ("bookmarks.html", f, "text/html")}
        )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "bookmarks" in data["data"]
    bookmarks = data["data"]["bookmarks"]
    assert len(bookmarks) > 0
    
    # Verify bookmark structure
    urls = [b["url"] for b in bookmarks]
    assert "https://python.org" in urls
    assert "https://docs.python.org" in urls
    assert "https://news.ycombinator.com" in urls

def test_categorize_bookmarks():
    """Test bookmark categorization."""
    # Sample bookmarks for categorization
    bookmarks = [
        {"url": "https://python.org", "title": "Python"},
        {"url": "https://docs.python.org", "title": "Python Documentation"},
        {"url": "https://news.ycombinator.com", "title": "Hacker News"}
    ]
    
    # Send categorization request
    response = client.post(
        "/categorize",
        json={"bookmarks": bookmarks}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "categories" in data["data"]
    categories = data["data"]["categories"]
    assert len(categories) > 0

def test_empty_bookmarks():
    """Test handling of empty bookmark list."""
    response = client.post(
        "/categorize",
        json={"bookmarks": []}
    )
    assert response.status_code == 400
