"""Structure agent for optimizing bookmark organization."""
import logging
from typing import List, Dict, Any
from langchain.schema import HumanMessage, SystemMessage

from agents.base import BaseAgent


class StructureAgent(BaseAgent):
    """Agent for organizing bookmarks into a logical folder structure."""

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the structure agent."""
        return """You are a bookmark structure optimization agent. Your task is to analyze
        bookmarks and create an intuitive folder hierarchy based on their categories and content.
        
        Guidelines:
        1. Create a clear and logical folder hierarchy
        2. Group related categories together
        3. Use subfolders for better organization
        4. Keep the structure balanced and not too deep
        5. Maintain meaningful folder names
        
        The output should be a JSON object representing the folder structure:
        {
            "folders": [
                {
                    "name": "Folder Name",
                    "bookmarks": [...],
                    "subfolders": [...]
                }
            ]
        }
        """

    async def optimize_structure(
        self,
        bookmarks: List[Dict],
        existing_structure: Dict = None
    ) -> Dict:
        """Optimize the folder structure for a set of bookmarks.
        
        Args:
            bookmarks: List of bookmark dictionaries
            existing_structure: Optional existing folder structure
            
        Returns:
            Optimized folder structure
        """
        if not bookmarks:
            return {"folders": []}
            
        try:
            # Convert bookmarks to a formatted string
            bookmarks_str = "\n".join(
                f"- Title: {b.get('title', 'Untitled')}\n  URL: {b.get('url', 'No URL')}\n  Category: {b.get('category', 'Uncategorized')}"
                for b in bookmarks
            )
            
            prompt = f"""Please organize these bookmarks into a logical folder structure:

            Bookmarks:
            {bookmarks_str}

            Create a folder hierarchy that:
            1. Groups related bookmarks together
            2. Uses meaningful folder names
            3. Creates subfolders when appropriate
            4. Maintains a balanced structure

            Respond with a JSON object containing the folder structure.
            Each folder should have:
            - name: folder name
            - bookmarks: list of bookmark objects
            - subfolders: list of subfolder objects
            """
            
            response = await self._process(prompt, context={
                "num_bookmarks": len(bookmarks),
                "has_existing_structure": existing_structure is not None
            })
            
            # Parse and validate the response
            import json
            structure = json.loads(response)
            
            if not isinstance(structure, dict) or "folders" not in structure:
                raise ValueError("Invalid structure format")
                
            return structure
            
        except Exception as e:
            # If something goes wrong, return a simple flat structure
            return {
                "folders": [
                    {
                        "name": "All Bookmarks",
                        "bookmarks": bookmarks,
                        "subfolders": []
                    }
                ]
            }

    async def process(self, input_data: Dict) -> Dict:
        """Process input data using the agent.
        
        Args:
            input_data: Dictionary containing input data
            
        Returns:
            Processed output data
        """
        bookmarks = input_data.get("bookmarks", [])
        existing_structure = input_data.get("existing_structure")
        
        structure = await self.optimize_structure(bookmarks, existing_structure)
        return {"structure": structure}
