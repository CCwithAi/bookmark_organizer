"""Categorizer agent for organizing bookmarks into meaningful categories."""
import logging
from typing import List, Dict, Any
import json
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CategorizerAgent:
    """Agent responsible for categorizing bookmarks."""

    def __init__(self, llm=None):  # Make llm optional since we're using direct API
        """Initialize the agent."""
        self.system_prompt = self._get_system_prompt()
        logger.info("Initialized categorizer agent")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for bookmark categorization."""
        return """You are an expert bookmark categorizer. Your task is to analyze bookmarks 
        and organize them into meaningful categories based on their content, URL, and title.
        
        Follow these guidelines:
        1. Create intuitive, user-friendly category names
        2. Group similar bookmarks together
        3. Consider both the content topic and purpose of the bookmark
        4. Use hierarchical categorization when appropriate
        5. Handle ambiguous cases by choosing the most relevant category
        
        IMPORTANT: You must ALWAYS respond with valid JSON in this exact format:
        {
            "category_name": [
                {"title": "bookmark title", "url": "bookmark url"},
                {"title": "another title", "url": "another url"}
            ],
            "another_category": [
                {"title": "third title", "url": "third url"}
            ]
        }
        
        Common categories to consider:
        - Development & Programming
        - Research & Education
        - Entertainment & Media
        - Shopping & E-commerce
        - Social Media & Communication
        - News & Current Events
        - Tools & Utilities
        - Business & Finance
        - Travel & Places
        - Health & Wellness
        
        Never include any explanatory text or markdown formatting. Only output valid JSON."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _process(self, prompt: str) -> str:
        """Process a message using Ollama API directly."""
        try:
            logger.debug("Sending request to Ollama")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama31-8b-extended",  # Changed back to the correct model name
                        "prompt": prompt,
                        "system": self.system_prompt,
                        "format": "json",
                        "temperature": 0.1,
                        "num_predict": 2048,
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                
                # Collect all response chunks
                full_response = ""
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "error" in data:
                            raise ValueError(f"Ollama API error: {data['error']}")
                        if "response" in data:
                            full_response += data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Ollama response line: {line}")
                        raise ValueError(f"Invalid response from Ollama: {str(e)}")
                
                logger.debug(f"Received response: {full_response[:200]}...")
                return full_response
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in Ollama API call: {str(e)}")
            raise ValueError(f"Failed to communicate with Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Error in Ollama API call: {str(e)}")
            raise ValueError(f"Failed to process with Ollama: {str(e)}")

    def _parse_response(self, response: str) -> Dict[str, List[Dict]]:
        """Parse the LLM response into a structured format."""
        try:
            # Clean up the response string
            response = response.strip()
            
            # Remove any markdown code block indicators
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            logger.debug(f"Cleaned response: {response[:200]}...")
            
            # Parse the JSON response
            data = json.loads(response)
            
            # Validate the structure
            if not isinstance(data, dict):
                raise ValueError("Response must be a dictionary")
            
            # Validate each category
            for category, bookmarks in data.items():
                if not isinstance(bookmarks, list):
                    raise ValueError(f"Category '{category}' must contain a list of bookmarks")
                
                # Validate each bookmark
                for bookmark in bookmarks:
                    if not isinstance(bookmark, dict):
                        raise ValueError(f"Invalid bookmark in category '{category}': {bookmark}")
                    if "title" not in bookmark or "url" not in bookmark:
                        raise ValueError(f"Bookmark missing required fields in category '{category}': {bookmark}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Failed to parse response: {str(e)}")

    async def categorize_bookmarks(self, bookmarks: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize a list of bookmarks."""
        if not bookmarks:
            logger.warning("No bookmarks provided to categorize")
            return {}

        # Process bookmarks in chunks of 10 to stay within context limits
        CHUNK_SIZE = 10
        all_categories: Dict[str, List[Dict]] = {}
        failed_chunks = []
        
        for i in range(0, len(bookmarks), CHUNK_SIZE):
            chunk = bookmarks[i:i + CHUNK_SIZE]
            chunk_num = i//CHUNK_SIZE + 1
            total_chunks = (len(bookmarks) + CHUNK_SIZE - 1)//CHUNK_SIZE
            logger.info(f"Processing chunk {chunk_num} of {total_chunks}")
            
            # Prepare the chunk data for the prompt
            bookmark_data = []
            for b in chunk:
                bookmark_data.append({
                    'title': b.get('title', 'Untitled'),
                    'url': b.get('url', ''),
                    'folder': b.get('folder', '')
                })
            
            # Create the prompt for this chunk
            prompt = f"""Please categorize these bookmarks into meaningful groups:
            {json.dumps(bookmark_data, indent=2)}
            
            IMPORTANT: Respond with ONLY valid JSON in the exact format shown in the system prompt.
            Do not include any other text or explanations."""
            
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    # Get categorization for this chunk
                    response = await self._process(prompt)
                    logger.debug(f"Received response for chunk {chunk_num}: {response[:200]}...")
                    
                    chunk_categories = self._parse_response(response)
                    if not chunk_categories:
                        raise ValueError("Empty response from LLM")
                        
                    logger.debug(f"Parsed categories for chunk {chunk_num}: {json.dumps(chunk_categories, indent=2)}")
                    
                    # Merge chunk categories with overall categories
                    for category, items in chunk_categories.items():
                        if category not in all_categories:
                            all_categories[category] = []
                        all_categories[category].extend(items)
                    
                    # Successfully processed this chunk
                    break
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error processing chunk {chunk_num} (attempt {retry_count}): {str(e)}")
                    if retry_count >= max_retries:
                        failed_chunks.append(chunk_num)
                        logger.error(f"Failed to process chunk {chunk_num} after {max_retries} attempts")
                    else:
                        logger.info(f"Retrying chunk {chunk_num}...")
        
        if failed_chunks:
            logger.error(f"Failed to process chunks: {failed_chunks}")
            if not all_categories:
                raise ValueError(f"Failed to categorize any bookmarks. Failed chunks: {failed_chunks}")
        
        logger.info(f"Successfully categorized bookmarks into {len(all_categories)} categories")
        return all_categories

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process bookmarks for categorization."""
        try:
            bookmarks = data.get('bookmarks', [])
            logger.info(f"Processing {len(bookmarks)} bookmarks for categorization")
            
            # Log a sample of bookmarks for debugging
            sample_size = min(3, len(bookmarks))
            if sample_size > 0:
                logger.debug("Sample of bookmarks:")
                for i in range(sample_size):
                    logger.debug(f"  {i+1}. Title: {bookmarks[i].get('title', 'No title')}")
                    logger.debug(f"     URL: {bookmarks[i].get('url', 'No URL')}")
            
            categories = await self.categorize_bookmarks(bookmarks)
            
            if not categories:
                error_msg = "Categorization failed - no categories returned"
                logger.error(error_msg)
                return {
                    'error': error_msg,
                    'categories': None
                }
            
            # Log categorization results
            logger.info(f"Successfully categorized into {len(categories)} categories:")
            for category, items in categories.items():
                logger.info(f"  - {category}: {len(items)} bookmarks")
                
            return {'categories': categories}
            
        except Exception as e:
            error_msg = f"Failed to process bookmarks: {str(e)}"
            logger.exception(error_msg)
            return {
                'error': error_msg,
                'categories': None
            }
