"""Streamlit frontend for the Bookmark Master application."""
import streamlit as st
import httpx
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential

# Constants
API_URL = "http://localhost:8080"
SUPPORTED_BROWSERS = ["Chrome", "Opera", "Edge"]

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure the app
st.set_page_config(
    page_title="Bookmark Master",
    page_icon="🔖",
    layout="wide",
)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def make_api_request(
    endpoint: str,
    method: str = "POST",
    files: Optional[Dict] = None,
    json_data: Optional[Dict] = None
) -> Tuple[bool, Dict]:
    """Make an API request with retry logic.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        files: Files to upload
        json_data: JSON data to send
        
    Returns:
        Tuple of (success, response_data)
    """
    try:
        # Clean up the endpoint path
        endpoint = endpoint.strip('/')
        url = f"{API_URL.rstrip('/')}/{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        
        async with httpx.AsyncClient() as client:
            if method == "POST":
                if files:
                    logger.debug(f"Sending file upload: {files.get('file', ('no file',))[0]}")
                    response = await client.post(url, files=files)
                else:
                    logger.debug("Sending JSON data")
                    response = await client.post(url, json=json_data)
            else:
                response = await client.get(url)
            
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            return True, response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {str(e)}")
        return False, {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False, {"error": str(e)}

async def process_file(file):
    """Process uploaded bookmarks file.
    
    Args:
        file: Uploaded bookmarks file
        
    Returns:
        Tuple of (success, data)
    """
    # Prepare the file for upload
    files = {
        'file': (
            file.name,  # Use the actual filename
            file.getvalue(),  # Get the file content
            'text/html'  # Set the content type
        )
    }
    
    # Import bookmarks
    logger.debug(f"Sending import request with file: {file.name}")
    success, response = await make_api_request("api/import-bookmarks", files=files)
    if not success:
        st.error(f"Failed to import bookmarks: {response.get('error')}")
        return False, {"error": response.get('error')}
    
    # Extract bookmarks from the response data
    if response.get("success") and response.get("data", {}).get("bookmarks"):
        bookmarks = response["data"]["bookmarks"]
        return True, {"bookmarks": bookmarks}
    else:
        error_msg = response.get("message", "No bookmarks found in file")
        st.error(f"Failed to import bookmarks: {error_msg}")
        return False, {"error": error_msg}

async def export_bookmarks(categories):
    """Export organized bookmarks as HTML file.
    
    Args:
        categories: Organized bookmark categories
        
    Returns:
        HTML content if successful, None otherwise
    """
    success, result = await make_api_request(
        "api/export-bookmarks",
        json_data={"categories": categories}
    )
    
    if success:
        return result
    else:
        st.error(f"Failed to export bookmarks: {result.get('error')}")
        return None

def main():
    """Main application function."""
    st.title("🔖 Bookmark Master")
    st.write("Upload your browser bookmarks and let AI organize them for you!")

    # Initialize session state for storing uploaded bookmarks
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "processed_bookmarks" not in st.session_state:
        st.session_state.processed_bookmarks = None
    if "organized_bookmarks" not in st.session_state:
        st.session_state.organized_bookmarks = None

    # File uploader section
    st.subheader("1. Upload Bookmark Files")
    uploaded_files = st.file_uploader(
        "Upload your bookmark HTML files",
        type=["html"],
        accept_multiple_files=True,
        help="You can upload bookmark exports from Chrome, Firefox, Opera, or other browsers"
    )

    # Process button and progress tracking
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        if st.button("Process Bookmarks", type="primary"):
            with st.spinner("Processing bookmarks..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                error_details = st.empty()
                
                # Process each file
                all_bookmarks = []
                total_files = len(uploaded_files)
                
                for i, file in enumerate(uploaded_files):
                    progress = (i / total_files) * 0.5
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {file.name}...")
                    
                    success, data = asyncio.run(process_file(file))
                    if success and "bookmarks" in data:
                        bookmarks = data["bookmarks"]
                        all_bookmarks.extend(bookmarks)
                        status_text.text(f"Found {len(bookmarks)} bookmarks in {file.name}")
                    else:
                        error_msg = f"Failed to process {file.name}: {data.get('error', 'Unknown error')}"
                        logger.error(error_msg)
                        st.error(error_msg)
                
                # Only proceed with categorization if we found bookmarks
                if all_bookmarks:
                    progress_bar.progress(0.5)
                    status_text.text(f"Organizing {len(all_bookmarks)} bookmarks...")
                    
                    try:
                        success, result = asyncio.run(make_api_request(
                            "api/categorize",
                            json_data={"bookmarks": all_bookmarks}
                        ))
                        
                        if success and result.get("success"):
                            st.session_state.organized_bookmarks = result["data"]["categories"]
                            progress_bar.progress(1.0)
                            status_text.text(f"Done! Organized {len(all_bookmarks)} bookmarks into {len(result['data']['categories'])} categories.")
                        else:
                            error_msg = f"Failed to organize bookmarks: {result.get('message', 'Unknown error')}"
                            logger.error(error_msg)
                            if result.get('data') and result['data'].get('error'):
                                error_details.error(f"Error details: {result['data']['error']}")
                            st.error(error_msg)
                    except Exception as e:
                        logger.exception("Error during categorization")
                        st.error(f"Error during categorization: {str(e)}")
                        error_details.error(f"Full error: {repr(e)}")
                else:
                    st.error("No bookmarks found in any of the uploaded files.")

    # Display organized bookmarks
    if st.session_state.organized_bookmarks:
        st.subheader("2. Your Organized Bookmarks")
        
        # Add download button for the organized bookmarks
        if st.button("Export Organized Bookmarks", type="secondary"):
            with st.spinner("Generating export file..."):
                export_html = asyncio.run(export_bookmarks(st.session_state.organized_bookmarks))
                if export_html:
                    st.download_button(
                        "Download Bookmarks",
                        export_html,
                        "organized_bookmarks.html",
                        "text/html",
                        help="Download your organized bookmarks as an HTML file that can be imported into any browser"
                    )
        
        # Display categories and bookmarks
        total_bookmarks = sum(len(bookmarks) for bookmarks in st.session_state.organized_bookmarks.values())
        st.write(f"Found {total_bookmarks} bookmarks in {len(st.session_state.organized_bookmarks)} categories")
        
        for category, bookmarks in st.session_state.organized_bookmarks.items():
            with st.expander(f"📁 {category} ({len(bookmarks)} bookmarks)", expanded=True):
                for bookmark in bookmarks:
                    col1, col2 = st.columns([3, 7])
                    with col1:
                        st.markdown(f"[{bookmark['title']}]({bookmark['url']})")
                    with col2:
                        if "description" in bookmark:
                            st.text(bookmark["description"])

if __name__ == "__main__":
    main()
