"""
Base Agent Class for LumenAI
All specialized agents inherit from this base
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger


class BaseAgent(ABC):
    """
    Abstract base class for all LumenAI agents
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        logger.info(f"🤖 Agent '{name}' initialized")

    @abstractmethod
    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Process user request and generate response

        Args:
            user_id: User identifier
            message: User's message
            context: User context from memory
            metadata: Additional metadata

        Returns:
            Response string
        """
        pass

    async def can_handle(self, message: str, context: Dict) -> float:
        """
        Determine if this agent can handle the request
        Returns confidence score 0.0 - 1.0
        """
        return 0.0

    def get_info(self) -> Dict[str, str]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }

    async def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Helper method to call LLM
        """
        from backend.core.llm_engine import LLMEngine

        llm = LLMEngine()
        return await llm.generate(prompt=prompt, system_prompt=system_prompt)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
