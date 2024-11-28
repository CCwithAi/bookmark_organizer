"""FastAPI backend for the Bookmark Master application."""
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import OllamaLLM
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import asyncio
import json
import tempfile
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from parsers.chrome import ChromeBookmarkParser
from parsers.opera import OperaBookmarkParser
from agents.base import BaseAgent
from agents.categorizer import CategorizerAgent
from agents.parser import ParserAgent
from agents.structure import StructureAgent
from agents.quality import QualityAgent

# Initialize FastAPI app
app = FastAPI(title="Bookmark Master API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only. In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize parsers
chrome_parser = ChromeBookmarkParser()
opera_parser = OperaBookmarkParser()

# Initialize Ollama
try:
    llm = OllamaLLM(
        model="llama31-8b-extended",  # Extended model for larger context
        num_ctx=8192,  # Match the extended context length
        num_gpu=1,
        num_thread=8,
        temperature=0.1,  # Lower temperature for more focused outputs
        top_p=0.9,  # Slightly reduce randomness
        repeat_penalty=1.1,  # Prevent repetitive outputs
        format="json"  # Request JSON formatted responses
    )
    logger.info("Successfully initialized Ollama LLM with extended context and JSON format")
except Exception as e:
    logger.error(f"Failed to initialize Ollama LLM: {str(e)}")
    raise

# Initialize agents
try:
    parser_agent = ParserAgent(llm)
    categorizer_agent = CategorizerAgent()  # No need to pass llm anymore
    structure_agent = StructureAgent(llm)
    quality_agent = QualityAgent(llm)
    logger.info("Successfully initialized all agents")
except Exception as e:
    logger.error(f"Failed to initialize agents: {str(e)}")
    raise

class BookmarkImportRequest(BaseModel):
    """Request model for bookmark import."""
    content: str
    browser: str  # 'chrome', 'opera', or 'edge'

class BookmarkResponse(BaseModel):
    """Response model for bookmark operations."""
    success: bool
    message: str
    data: Optional[dict] = None
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BookmarkCategorizeRequest(BaseModel):
    """Request model for bookmark categorization."""
    bookmarks: List[dict]

class BookmarkStructureRequest(BaseModel):
    """Request model for bookmark structure optimization."""
    bookmarks: List[dict]
    categories: Dict[str, List[dict]]

class BookmarkExportRequest(BaseModel):
    """Request model for bookmark export."""
    categories: Dict[str, List[dict]]

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    logger.debug("Root endpoint called")
    return {"status": "ok", "message": "Bookmark Master API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/import", response_model=BookmarkResponse)
async def import_bookmarks(request: BookmarkImportRequest):
    """Import bookmarks from a browser export file."""
    logger.debug(f"Received import request for {request.browser} browser")
    try:
        logger.debug(f"Starting import for {request.browser} browser")
        logger.debug(f"Content length: {len(request.content)} characters")
        
        # Select appropriate parser
        parser = None
        if request.browser.lower() == "chrome":
            parser = chrome_parser
        elif request.browser.lower() == "opera":
            parser = opera_parser
        else:
            logger.error(f"Unsupported browser: {request.browser}")
            return BookmarkResponse(
                success=False,
                message=f"Unsupported browser: {request.browser}",
                data=None
            )
            
        # Parse bookmarks
        logger.debug("Starting bookmark parsing")
        root_folder = await parser.parse_content(request.content)
        logger.debug(f"Root folder parsed: {root_folder}")
        
        # Extract bookmarks from the folder structure
        bookmarks = []
        def extract_bookmarks(folder):
            logger.debug(f"Processing folder: {getattr(folder, 'name', 'unnamed')}")
            if hasattr(folder, 'bookmarks'):
                logger.debug(f"Found {len(folder.bookmarks)} bookmarks in folder")
                bookmarks.extend([
                    {
                        'url': b.url,
                        'title': b.title,
                        'description': b.description or '',
                        'tags': b.tags or [],
                        'folder_path': b.folder_path or [],
                        'source_browser': b.source_browser,
                        'added_date': b.added_date.isoformat() if b.added_date else None,
                        'last_modified': b.last_modified.isoformat() if b.last_modified else None
                    }
                    for b in folder.bookmarks
                ])
            
            if hasattr(folder, 'subfolders'):
                logger.debug(f"Found {len(folder.subfolders)} subfolders")
                for subfolder in folder.subfolders:
                    extract_bookmarks(subfolder)
            
        extract_bookmarks(root_folder)
        logger.debug(f"Extracted {len(bookmarks)} total bookmarks")
        
        # Validate extracted bookmarks
        logger.debug("Starting bookmark validation")
        valid_bookmarks = await validate_bookmarks(bookmarks)
        logger.debug(f"Validated {len(valid_bookmarks)} bookmarks")
        
        return BookmarkResponse(
            success=True,
            message=f"Successfully imported {len(valid_bookmarks)} bookmarks",
            data={"bookmarks": valid_bookmarks}
        )
        
    except Exception as e:
        logger.exception("Error during bookmark import")
        return BookmarkResponse(
            success=False,
            message=f"Error: {str(e)}",
            data=None
        )

@app.post("/api/categorize", response_model=BookmarkResponse)
async def categorize_bookmarks(request: BookmarkCategorizeRequest):
    """Categorize a list of bookmarks using the AI agent."""
    logger.debug(f"Received categorization request with {len(request.bookmarks)} bookmarks")
    try:
        if not request.bookmarks:
            logger.error("No bookmarks provided")
            return BookmarkResponse(
                success=False,
                message="No bookmarks provided",
                data=None
            )
            
        logger.info(f"Categorizing {len(request.bookmarks)} bookmarks")
        result = await categorizer_agent.process({"bookmarks": request.bookmarks})
        
        if not result or not result.get("categories"):
            logger.error("Categorization failed: No categories returned")
            return BookmarkResponse(
                success=False,
                message="Categorization failed: No categories returned",
                data=None
            )
            
        logger.info(f"Successfully categorized bookmarks into {len(result['categories'])} categories")
        return BookmarkResponse(
            success=True,
            message="Bookmarks categorized successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error during categorization: {str(e)}")
        return BookmarkResponse(
            success=False,
            message=f"Error during categorization: {str(e)}",
            data=None
        )

@app.post("/optimize-structure", response_model=BookmarkResponse)
async def optimize_structure(request: BookmarkStructureRequest):
    """Optimize the folder structure for a set of bookmarks."""
    logger.debug(f"Received structure optimization request with {len(request.bookmarks)} bookmarks")
    try:
        logger.info(f"Optimizing structure for {len(request.bookmarks)} bookmarks")
        # Extract bookmarks from categories and combine with uncategorized bookmarks
        categorized_bookmarks = []
        for category, bookmarks in request.categories.items():
            for bookmark in bookmarks:
                bookmark["category"] = category
                categorized_bookmarks.append(bookmark)
                
        result = await structure_agent.process({
            "bookmarks": categorized_bookmarks,
            "existing_structure": None
        })
        
        logger.info("Successfully optimized folder structure")
        return BookmarkResponse(
            success=True,
            message="Folder structure optimized successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error during structure optimization: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/validate")
async def validate_bookmarks(bookmarks: List[dict]):
    """Validate and clean up bookmarks."""
    logger.debug(f"Received validation request with {len(bookmarks)} bookmarks")
    try:
        logger.info(f"Validating {len(bookmarks)} bookmarks")
        
        # Simple validation: ensure required fields are present and non-empty
        validated = []
        for bookmark in bookmarks:
            logger.debug(f"Validating bookmark: {bookmark}")
            if bookmark.get('url'):  # Only URL is required
                if not bookmark.get('title'):
                    bookmark['title'] = bookmark['url']  # Use URL as title if missing
                validated.append(bookmark)
                logger.debug(f"Bookmark validated: {bookmark}")
            else:
                logger.warning(f"Invalid bookmark (missing URL): {bookmark}")
                
        logger.info(f"Successfully validated {len(validated)} out of {len(bookmarks)} bookmarks")
        return validated
    except Exception as e:
        logger.error(f"Error during bookmark validation: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/import-bookmarks")
async def import_bookmarks(file: UploadFile = File(...)):
    """Import bookmarks from an HTML file."""
    try:
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        logger.debug(f"Received file upload: {file.filename}")
        
        try:
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            logger.debug(f"Saved uploaded file to: {temp_file.name}")
            
            # Initialize parser based on file type
            parser = ChromeBookmarkParser()  # For now, only support Chrome/Edge
            logger.debug("Initialized Chrome parser")
            
            # Parse bookmarks
            bookmarks = []
            if parser.max_bookmarks_per_chunk:
                async for folder in parser.parse_file(temp_file.name):
                    if isinstance(folder, dict):
                        bookmarks.extend(folder.get('bookmarks', []))
                    elif hasattr(folder, 'bookmarks'):
                        bookmarks.extend(folder.bookmarks)
                    else:
                        logger.warning(f"Unexpected folder type: {type(folder)}")
            else:
                folder = await parser.parse_file(temp_file.name)
                if isinstance(folder, dict):
                    bookmarks.extend(folder.get('bookmarks', []))
                elif hasattr(folder, 'bookmarks'):
                    bookmarks.extend(folder.bookmarks)
                else:
                    logger.warning(f"Unexpected folder type: {type(folder)}")
            logger.debug(f"Processed {len(bookmarks)} bookmarks")
            
            # Clean up temp file
            os.unlink(temp_file.name)
            logger.debug("Cleaned up temporary file")
            
            # Process bookmarks through agents
            logger.debug(f"Received categorization request with {len(bookmarks)} bookmarks")
            logger.info(f"Categorizing {len(bookmarks)} bookmarks")
            
            result = await categorizer_agent.process({'bookmarks': bookmarks})
            
            if 'error' in result:
                logger.error(f"Categorization failed: {result['error']}")
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Failed to organize bookmarks: {result['error']}"}
                )
            
            return result
            
        finally:
            # Ensure temp file is cleaned up
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.exception("Failed to process bookmarks")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process bookmarks: {str(e)}"}
        )

@app.post("/api/export-bookmarks")
async def export_bookmarks(request: BookmarkExportRequest) -> Response:
    """Export organized bookmarks as an HTML file."""
    try:
        categories = request.categories
        if not categories:
            raise ValueError("No categories provided")
            
        # Generate HTML
        html = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Bookmarks</TITLE>",
            "<H1>Bookmarks Menu</H1>",
            "<DL><p>"
        ]
        
        for category, bookmarks in categories.items():
            # Add category folder
            html.extend([
                f'    <DT><H3>{category}</H3>',
                "    <DL><p>"
            ])
            
            # Add bookmarks
            for bookmark in bookmarks:
                description = bookmark.get("description", "")
                add_date = bookmark.get("add_date", "")
                last_modified = bookmark.get("last_modified", "")
                
                attributes = [
                    f'HREF="{bookmark["url"]}"',
                    f'ADD_DATE="{add_date}"' if add_date else "",
                    f'LAST_MODIFIED="{last_modified}"' if last_modified else "",
                ]
                attributes = " ".join(filter(None, attributes))
                
                html.append(f'        <DT><A {attributes}>{bookmark["title"]}</A>')
                if description:
                    html.append(f'        <DD>{description}')
                    
            html.append("    </DL><p>")
            
        html.append("</DL><p>")
        
        # Return HTML file
        return Response(
            content="\n".join(html),
            media_type="text/html",
            headers={
                "Content-Disposition": "attachment; filename=organized_bookmarks.html"
            }
        )
            
    except Exception as e:
        logger.error(f"Failed to export bookmarks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export bookmarks: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, timeout_keep_alive=120)
