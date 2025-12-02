"""
LumenAI LLM Engine
Unified interface for interacting with various LLM providers
"""

from typing import Optional, Dict, Any, List
from loguru import logger
import os

from backend.shared.config.settings import settings


class LLMEngine:
    """
    Unified LLM interface supporting multiple providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Local models (future)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.model = model or settings.DEFAULT_MODEL

        self._initialize_client()

        logger.info(f"🤖 LLM Engine initialized: {self.provider}/{self.model}")

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        try:
            if self.provider == "openai":
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY
                )

            elif self.provider == "anthropic":
                import anthropic
                self.client = anthropic.AsyncAnthropic(
                    api_key=settings.ANTHROPIC_API_KEY
                )

            else:
                logger.warning(f"Unknown provider: {self.provider}, using mock")
                self.client = None

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> str:
        """
        Generate response from LLM
        """
        try:
            if self.provider == "openai":
                return await self._generate_openai(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format
                )

            elif self.provider == "anthropic":
                return await self._generate_anthropic(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            else:
                # Fallback mock response
                return await self._generate_mock(prompt)

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "Przepraszam, wystąpił problem z generowaniem odpowiedzi. Spróbuj ponownie."

    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str]
    ) -> str:
        """Generate using OpenAI API"""

        if not self.client:
            return await self._generate_mock(prompt)

        messages = []

        # System message
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add context from memory
        if context and context.get("recent_messages"):
            for msg in context["recent_messages"][-3:]:  # Last 3 messages
                messages.append({"role": "user", "content": msg.get("user_message", "")})
                messages.append({"role": "assistant", "content": msg.get("assistant_response", "")})

        # Current prompt
        messages.append({"role": "user", "content": prompt})

        # API call
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        return response.choices[0].message.content

    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Anthropic Claude API"""

        if not self.client:
            return await self._generate_mock(prompt)

        messages = []

        # Add context
        if context and context.get("recent_messages"):
            for msg in context["recent_messages"][-3:]:
                messages.append({"role": "user", "content": msg.get("user_message", "")})
                messages.append({"role": "assistant", "content": msg.get("assistant_response", "")})

        # Current message
        messages.append({"role": "user", "content": prompt})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages
        )

        return response.content[0].text

    async def _generate_mock(self, prompt: str) -> str:
        """Mock response for development without API keys"""
        return f"[MOCK RESPONSE] Rozumiem pytanie: '{prompt[:50]}...'. To jest symulowana odpowiedź LumenAI dla celów deweloperskich. Skonfiguruj API key w .env aby używać prawdziwych modeli."

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Generate streaming response (for real-time chat)
        TODO: Implement streaming support
        """
        # For now, return full response
        response = await self.generate(prompt, system_prompt, **kwargs)
        yield response
