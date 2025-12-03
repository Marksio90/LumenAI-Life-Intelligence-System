"""
Smart Model Router
Automatically selects the cheapest model for the task complexity
"""

from typing import Dict, Literal
from loguru import logger

from backend.shared.config.settings import settings


ModelTier = Literal["fast", "default", "smart"]


class SmartModelRouter:
    """
    Intelligently route requests to appropriate models based on:
    - Task complexity
    - Required reasoning depth
    - Cost optimization
    """

    def __init__(self):
        self.models = {
            "fast": settings.FAST_MODEL,        # gpt-3.5-turbo - Ultra cheap
            "default": settings.DEFAULT_MODEL,  # gpt-4o-mini - Best balance
            "smart": settings.SMART_MODEL,      # gpt-4o - Complex tasks
        }

    def select_model(
        self,
        prompt: str,
        task_type: str = "general",
        force_tier: ModelTier = None
    ) -> str:
        """
        Select appropriate model based on task complexity

        Args:
            prompt: User's prompt
            task_type: Type of task (simple, analysis, complex, creative)
            force_tier: Force specific tier (for testing)

        Returns:
            Model name to use
        """

        if force_tier:
            return self.models[force_tier]

        if not settings.ENABLE_SMART_ROUTING:
            return self.models["default"]

        # Analyze complexity
        complexity = self._analyze_complexity(prompt, task_type)

        # Route based on complexity
        if complexity == "simple":
            tier = "fast"
        elif complexity == "complex":
            tier = "smart"
        else:
            tier = "default"

        model = self.models[tier]

        logger.debug(
            f"🧠 Smart routing: {complexity} task → {model} "
            f"(prompt length: {len(prompt)})"
        )

        return model

    def _analyze_complexity(self, prompt: str, task_type: str) -> str:
        """Analyze task complexity"""

        # Length-based heuristic
        prompt_length = len(prompt)

        # Complex indicators
        complex_keywords = [
            "analyze", "compare", "evaluate", "complex", "detailed",
            "comprehensive", "explain in depth", "philosophical",
            "strategic", "multi-step", "reasoning"
        ]

        # Simple indicators
        simple_keywords = [
            "quick", "simple", "brief", "short", "yes/no",
            "list", "name", "what is", "define"
        ]

        prompt_lower = prompt.lower()

        # Check for complex patterns
        has_complex = any(kw in prompt_lower for kw in complex_keywords)
        has_simple = any(kw in prompt_lower for kw in simple_keywords)

        # Decision logic
        if task_type == "intent_classification":
            return "fast"  # Simple classification
        elif task_type == "complex_reasoning":
            return "complex"
        elif has_simple and not has_complex:
            return "simple"
        elif has_complex or prompt_length > 1000:
            return "complex"
        else:
            return "medium"  # Default - balanced

    def get_model_for_agent(self, agent_name: str) -> str:
        """Get recommended model for specific agent"""

        # Agent-specific model selection
        agent_models = {
            "planner": "default",       # Standard planning
            "mood": "default",          # Emotional support needs quality
            "decision": "smart",        # Complex decisions need reasoning
            "vision": "smart",          # Vision analysis
            "general": "default",       # General chat
        }

        tier = agent_models.get(agent_name, "default")
        return self.models[tier]


# Global router instance
model_router = SmartModelRouter()
