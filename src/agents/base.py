"""Base agent class for bookmark processing."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from pydantic.v1 import ConfigDict

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all bookmark processing agents."""
    
    # Use Pydantic v2 configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, llm: BaseLLM):
        """Initialize the agent with a language model."""
        self.llm = llm
        self.system_prompt = self._get_system_prompt()
        logger.info(f"Initialized {self.__class__.__name__} with system prompt")
        
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _process(
        self,
        human_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a message using the language model."""
        try:
            logger.debug(f"Processing message with {self.__class__.__name__}")
            logger.debug(f"Human message: {human_message[:200]}...")
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=human_message)
            ]
            
            if context:
                context_str = "\nContext:\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
                messages.append(HumanMessage(content=context_str))
                logger.debug(f"Added context: {context_str[:200]}...")
            
            # Add timeout to LLM call
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages),
                    timeout=60  # 60 second timeout
                )
                logger.debug(f"Received response: {response.content[:200]}...")
                return response.content
            except asyncio.TimeoutError:
                logger.error("LLM call timed out after 60 seconds")
                raise RuntimeError("LLM call timed out")
                
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}._process: {str(e)}")
            raise
        
    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """Process input data according to the agent's specific task."""
        pass
