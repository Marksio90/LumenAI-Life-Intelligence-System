"""
LumenAI Core Orchestrator
Central intelligence that routes requests to appropriate agents
"""

from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio
from datetime import datetime

from core.memory import MemoryManager
from core.llm_engine import LLMEngine
from agents.base import BaseAgent


class Orchestrator:
    """
    The brain of LumenAI - routes user requests to appropriate specialized agents
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.llm_engine = LLMEngine()
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all specialized agents"""
        logger.info("🧠 Initializing agents...")

        # Import agents dynamically to avoid circular imports
        try:
            from agents.cognitive.planner_agent import PlannerAgent
            from agents.emotional.mood_agent import MoodAgent
            from agents.cognitive.decision_agent import DecisionAgent
            from agents.vision.vision_agent import VisionAgent
            from agents.speech.speech_agent import SpeechAgent
            from agents.planning.finance_agent import FinanceAgent
            from agents.automation.automation_agent import AutomationAgent

            self.agents = {
                "planner": PlannerAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "mood": MoodAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "decision": DecisionAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "vision": VisionAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "speech": SpeechAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "finance": FinanceAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
                "automation": AutomationAgent(memory_manager=self.memory_manager, llm_engine=self.llm_engine),
            }

            logger.info(f"✅ Initialized {len(self.agents)} agents: {list(self.agents.keys())}")

        except Exception as e:
            logger.warning(f"⚠️ Some agents could not be loaded: {e}")
            # Create fallback agent
            self.agents = {"general": None}

    async def process_message(
        self,
        user_id: str,
        message: str,
        message_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main processing pipeline:
        1. Analyze intent
        2. Route to appropriate agent(s)
        3. Generate response
        4. Update memory
        """
        try:
            logger.info(f"Processing message from {user_id}: {message[:50]}...")

            # Get user context from memory
            context = await self.memory_manager.get_user_context(user_id)

            # Check if message type explicitly indicates agent
            if message_type == "image":
                agent_name = "vision"
                confidence = 1.0
                context["has_image"] = True
            elif message_type == "audio" or message_type == "tts":
                agent_name = "speech"
                confidence = 1.0
                context["has_audio"] = True
            else:
                # Analyze intent and determine which agent(s) to use
                intent_analysis = await self._analyze_intent(message, context, metadata)
                agent_name = intent_analysis["primary_agent"]
                confidence = intent_analysis["confidence"]

            logger.info(f"Intent: {agent_name} (confidence: {confidence:.2f})")

            # Route to agent
            if agent_name in self.agents and self.agents[agent_name]:
                agent = self.agents[agent_name]
                response_content = await agent.process(
                    user_id=user_id,
                    message=message,
                    context=context,
                    metadata=metadata
                )
            else:
                # Fallback to general LLM response
                response_content = await self._general_response(message, context)
                agent_name = "general"

            # Store interaction in memory
            await self.memory_manager.store_interaction(
                user_id=user_id,
                message=message,
                response=response_content,
                agent=agent_name,
                metadata=metadata
            )

            return {
                "content": response_content,
                "agent": agent_name,
                "confidence": confidence,
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_type": message_type
                }
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "content": "Przepraszam, wystąpił błąd. Spróbuj ponownie.",
                "agent": "error",
                "error": str(e)
            }

    async def _analyze_intent(self, message: str, context: Dict, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze user's intent to determine which agent should handle the request
        Uses LLM to classify intent
        """

        # Check metadata for hints
        if metadata:
            if metadata.get("image"):
                return {"primary_agent": "vision", "confidence": 1.0, "reasoning": "image provided"}
            if metadata.get("audio"):
                return {"primary_agent": "speech", "confidence": 1.0, "reasoning": "audio provided"}

        # Intent classification prompt
        classification_prompt = f"""
Analyze the following user message and determine which specialized agent should handle it.

Available agents:
- planner: Scheduling, calendar, tasks, reminders, time management
- mood: Emotional support, mental health, feelings, therapy
- decision: Life decisions, choices, dilemmas, advice
- finance: Money, budget, expenses, savings goals, financial planning, tracking spending
- vision: Image analysis, photo interpretation, OCR, object detection
- speech: Audio transcription, voice commands, text-to-speech
- automation: Sending emails, calendar integration, note creation, webhooks, external API integrations
- general: General conversation, questions not fitting other categories

User message: "{message}"

Recent context: {context.get('recent_summary', 'No recent context')}

Respond with JSON:
{{
    "primary_agent": "agent_name",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}
"""

        try:
            result = await self.llm_engine.generate(
                prompt=classification_prompt,
                response_format="json"
            )

            # Parse result
            import json
            parsed = json.loads(result)

            return {
                "primary_agent": parsed.get("primary_agent", "general"),
                "confidence": parsed.get("confidence", 0.5),
                "reasoning": parsed.get("reasoning", "")
            }

        except Exception as e:
            logger.error(f"Intent analysis error: {e}")
            # Fallback to keyword-based routing
            return self._fallback_intent_analysis(message)

    def _fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Simple keyword-based intent detection as fallback"""
        message_lower = message.lower()

        keywords = {
            "planner": ["plan", "kalendarz", "zadanie", "przypomnienie", "spotkanie", "termin"],
            "mood": ["czuję", "emocje", "smutek", "stres", "niepokój", "radość"],
            "decision": ["decyzja", "wybór", "czy powinienem", "pomóż zdecydować"],
            "finance": ["pieniądze", "budżet", "wydatki", "oszczędności", "koszty", "wydałem", "zapłaciłem"],
            "vision": ["obraz", "zdjęcie", "foto", "co widzisz", "przeczytaj tekst", "ocr"],
            "speech": ["nagraj", "przeczytaj", "powiedz", "transkrypcja", "audio"],
            "automation": ["wyślij", "email", "kalendarz", "notatka", "webhook", "automatyzacja", "integracja"],
        }

        for agent, words in keywords.items():
            if any(word in message_lower for word in words):
                return {
                    "primary_agent": agent,
                    "confidence": 0.7,
                    "reasoning": "keyword match"
                }

        return {
            "primary_agent": "general",
            "confidence": 0.5,
            "reasoning": "no clear match"
        }

    async def _general_response(self, message: str, context: Dict) -> str:
        """Generate general response using LLM"""

        system_prompt = """
Jesteś LumenAI - osobisty asystent życia i cyfrowy mentor.

Twoim zadaniem jest pomagać użytkownikom w codziennych wyzwaniach:
- Planowanie i organizacja
- Wsparcie emocjonalne
- Podejmowanie decyzji
- Rozwój osobisty
- Praktyczne porady życiowe

Bądź ciepły, empatyczny, ale konkretny. Pytaj o szczegóły gdy potrzeba.
Mów po polsku w naturalny, przyjazny sposób.
"""

        user_prompt = f"Użytkownik: {message}"

        response = await self.llm_engine.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            context=context
        )

        return response

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "total_agents": len(self.agents),
            "active_agents": [name for name, agent in self.agents.items() if agent],
            "status": "operational"
        }
