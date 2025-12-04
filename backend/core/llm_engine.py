"""
LumenAI LLM Engine
Unified interface for interacting with various LLM providers
Now with COST OPTIMIZATION! 💰
"""

from typing import Optional, Dict, Any, List
from loguru import logger
import os
import hashlib
import json

from backend.shared.config.settings import settings
from backend.core.cost_tracker import cost_tracker
from backend.core.model_router import model_router


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
        model: Optional[str] = None,
        use_smart_routing: bool = True
    ):
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.model = model or settings.DEFAULT_MODEL
        self.use_smart_routing = use_smart_routing and settings.ENABLE_SMART_ROUTING

        # Cache for responses (simple in-memory cache)
        self.cache = {} if settings.ENABLE_RESPONSE_CACHE else None

        self._initialize_client()

        logger.info(
            f"🤖 LLM Engine initialized: {self.provider}/{self.model} | "
            f"Smart Routing: {self.use_smart_routing} | "
            f"Caching: {settings.ENABLE_RESPONSE_CACHE}"
        )

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
        max_tokens: int = None,
        response_format: Optional[str] = None,
        task_type: str = "general",
        force_model: Optional[str] = None
    ) -> str:
        """
        Generate response from LLM with cost optimization
        """

        # Smart model selection
        if force_model:
            selected_model = force_model
        elif self.use_smart_routing:
            selected_model = model_router.select_model(prompt, task_type)
        else:
            selected_model = self.model

        # Set appropriate max_tokens
        if max_tokens is None:
            if selected_model == settings.SMART_MODEL:
                max_tokens = settings.MAX_TOKENS_SMART
            else:
                max_tokens = settings.MAX_TOKENS_DEFAULT

        # Check cache first
        if self.cache is not None:
            cache_key = self._get_cache_key(prompt, system_prompt, selected_model)
            if cache_key in self.cache:
                logger.info(f"💾 Cache HIT! Saved API call for: {prompt[:50]}...")
                return self.cache[cache_key]

        try:
            if self.provider == "openai":
                response = await self._generate_openai(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    model=selected_model
                )

            elif self.provider == "anthropic":
                response = await self._generate_anthropic(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=selected_model
                )

            else:
                # Fallback mock response
                response = await self._generate_mock(prompt)

            # Cache the response
            if self.cache is not None:
                cache_key = self._get_cache_key(prompt, system_prompt, selected_model)
                self.cache[cache_key] = response

            return response

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
        response_format: Optional[str],
        model: str
    ) -> str:
        """Generate using OpenAI API with cost tracking"""

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
            "model": model,  # Use selected model, not self.model
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        # Track cost
        usage = response.usage
        cost_tracker.track_request(
            model=model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens
        )

        return response.choices[0].message.content

    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> str:
        """Generate using Anthropic Claude API with cost tracking"""

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
            model=model,  # Use selected model
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages
        )

        # Track cost
        usage = response.usage
        cost_tracker.track_request(
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens
        )

        return response.content[0].text

    async def _generate_mock(self, prompt: str) -> str:
        """Mock response for development without API keys"""
        return f"[MOCK RESPONSE] Rozumiem pytanie: '{prompt[:50]}...'. To jest symulowana odpowiedź LumenAI dla celów deweloperskich. Skonfiguruj API key w .env aby używać prawdziwych modeli."

    # ============================================================================
    # TRUE STREAMING SUPPORT
    # ============================================================================

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        task_type: str = "general",
        force_model: Optional[str] = None
    ):
        """
        Generate streaming response from LLM.

        Yields tokens as they're generated for real-time display.

        Args:
            prompt: User input prompt
            system_prompt: System instructions for the AI
            context: Conversation context
            temperature: Randomness (0-2)
            max_tokens: Maximum tokens to generate
            task_type: Type of task for smart routing
            force_model: Force specific model

        Yields:
            str: Individual tokens from the model
        """

        # Smart model selection
        if force_model:
            selected_model = force_model
        elif self.use_smart_routing:
            selected_model = model_router.select_model(prompt, task_type)
        else:
            selected_model = self.model

        # Set appropriate max_tokens
        if max_tokens is None:
            if selected_model == settings.SMART_MODEL:
                max_tokens = settings.MAX_TOKENS_SMART
            else:
                max_tokens = settings.MAX_TOKENS_DEFAULT

        logger.info(f"🌊 Starting TRUE streaming with model: {selected_model}")

        try:
            if self.provider == "openai":
                async for token in self._stream_openai(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=selected_model
                ):
                    yield token

            elif self.provider == "anthropic":
                async for token in self._stream_anthropic(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=selected_model
                ):
                    yield token

            else:
                # Fallback mock streaming
                async for token in self._stream_mock(prompt):
                    yield token

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield f"Przepraszam, wystąpił problem z generowaniem odpowiedzi. Spróbuj ponownie. (Error: {e})"

    async def _stream_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict],
        temperature: float,
        max_tokens: int,
        model: str
    ):
        """
        Stream response from OpenAI API.

        Yields tokens as they arrive from the API.
        """

        if not self.client:
            async for token in self._stream_mock(prompt):
                yield token
            return

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

        # API call with streaming
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True  # Enable streaming
        )

        # Track tokens for cost calculation
        total_input_tokens = sum(len(m["content"].split()) for m in messages) * 1.3  # Estimate
        total_output_tokens = 0

        # Stream tokens
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    token = delta.content
                    total_output_tokens += len(token.split()) * 1.3  # Estimate
                    yield token

        # Track cost after streaming completes
        cost_tracker.track_request(
            model=model,
            input_tokens=int(total_input_tokens),
            output_tokens=int(total_output_tokens)
        )

        logger.info(f"✅ OpenAI streaming complete. Estimated tokens: {int(total_output_tokens)}")

    async def _stream_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict],
        temperature: float,
        max_tokens: int,
        model: str
    ):
        """
        Stream response from Anthropic Claude API.

        Yields tokens as they arrive from the API.
        """

        if not self.client:
            async for token in self._stream_mock(prompt):
                yield token
            return

        messages = []

        # Add context
        if context and context.get("recent_messages"):
            for msg in context["recent_messages"][-3:]:
                messages.append({"role": "user", "content": msg.get("user_message", "")})
                messages.append({"role": "assistant", "content": msg.get("assistant_response", "")})

        # Current message
        messages.append({"role": "user", "content": prompt})

        # API call with streaming
        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages
        ) as stream:
            # Track tokens
            total_input_tokens = 0
            total_output_tokens = 0

            async for text in stream.text_stream:
                yield text
                total_output_tokens += len(text.split()) * 1.3  # Estimate

            # Get final message for accurate token counts
            final_message = await stream.get_final_message()
            if final_message.usage:
                total_input_tokens = final_message.usage.input_tokens
                total_output_tokens = final_message.usage.output_tokens

                # Track cost after streaming completes
                cost_tracker.track_request(
                    model=model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens
                )

        logger.info(f"✅ Anthropic streaming complete. Tokens: {total_output_tokens}")

    async def _stream_mock(self, prompt: str):
        """Mock streaming for development without API keys"""
        import asyncio

        mock_response = f"[MOCK STREAMING] Rozumiem pytanie: '{prompt[:50]}...'. To jest symulowana odpowiedź streaming LumenAI dla celów deweloperskich. Skonfiguruj API key w .env aby używać prawdziwych modeli."

        # Simulate streaming by yielding words with delays
        words = mock_response.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)  # 50ms delay between words

    def _get_cache_key(self, prompt: str, system_prompt: Optional[str], model: str) -> str:
        """Generate cache key for response"""
        cache_str = f"{model}:{system_prompt}:{prompt}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get_cost_stats(self) -> Dict:
        """Get cost statistics"""
        return cost_tracker.get_stats()

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
