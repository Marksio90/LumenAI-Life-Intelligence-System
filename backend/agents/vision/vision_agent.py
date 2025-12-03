"""
Vision Agent - Image analysis, OCR, object detection
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import base64
import io
from PIL import Image
import pytesseract
from pathlib import Path

from backend.agents.base import BaseAgent


class VisionAgent(BaseAgent):
    """
    Specialized agent for vision and image analysis
    - OCR (text extraction from images)
    - Object detection
    - Scene description
    - Image understanding with GPT-4V
    """

    def __init__(self, memory_manager=None):
        super().__init__(
            name="Vision",
            description="Analiza obrazów, OCR, rozpoznawanie obiektów i scen",
            memory_manager=memory_manager
        )

        # Try to set tesseract path for different environments
        try:
            # Try common paths
            for path in ['/usr/bin/tesseract', '/usr/local/bin/tesseract']:
                if Path(path).exists():
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
        except Exception as e:
            logger.warning(f"Could not set tesseract path: {e}")

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process vision-related requests"""

        logger.info(f"Vision Agent processing for {user_id}")

        # Check if image data is provided in metadata
        if not metadata or "image" not in metadata:
            return "📸 Aby przeanalizować obraz, prześlij zdjęcie wraz z pytaniem!"

        image_data = metadata.get("image")
        analysis_type = await self._determine_analysis_type(message)

        try:
            # Load image
            image = await self._load_image(image_data)

            if analysis_type == "ocr":
                return await self._perform_ocr(image, message)
            elif analysis_type == "object_detection":
                return await self._detect_objects(image, message)
            elif analysis_type == "scene_description":
                return await self._describe_scene(image, message)
            else:
                # General AI-powered analysis with GPT-4V
                return await self._analyze_with_vision_model(image, message, image_data)

        except Exception as e:
            logger.error(f"Vision processing error: {e}")
            return f"❌ Wystąpił błąd podczas analizy obrazu: {str(e)}"

    async def _determine_analysis_type(self, message: str) -> str:
        """Determine what type of vision analysis is needed"""

        message_lower = message.lower()

        # OCR keywords
        if any(word in message_lower for word in [
            "tekst", "przeczytaj", "odczytaj", "co jest napisane",
            "text", "read", "ocr"
        ]):
            return "ocr"

        # Object detection
        if any(word in message_lower for word in [
            "co widzisz", "obiekty", "rzeczy", "przedmioty",
            "what do you see", "objects", "detect"
        ]):
            return "object_detection"

        # Scene description
        if any(word in message_lower for word in [
            "opisz", "scena", "co się dzieje", "describe", "scene"
        ]):
            return "scene_description"

        return "general"

    async def _load_image(self, image_data: Any) -> Image.Image:
        """Load image from various formats"""

        if isinstance(image_data, str):
            # Base64 encoded image
            if image_data.startswith('data:image'):
                # Remove data URL prefix
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            return Image.open(io.BytesIO(image_bytes))

        elif isinstance(image_data, bytes):
            return Image.open(io.BytesIO(image_data))

        elif isinstance(image_data, Image.Image):
            return image_data

        else:
            raise ValueError(f"Unsupported image data type: {type(image_data)}")

    async def _perform_ocr(self, image: Image.Image, message: str) -> str:
        """Extract text from image using OCR"""

        try:
            # Convert to grayscale for better OCR
            image_gray = image.convert('L')

            # Perform OCR with Polish and English
            text = pytesseract.image_to_string(image_gray, lang='pol+eng')

            if not text.strip():
                return "📄 Nie wykryto żadnego tekstu na obrazie. Upewnij się, że obraz zawiera czytelny tekst."

            # Let LLM format the response
            system_prompt = """
Użytkownik poprosił o odczytanie tekstu z obrazu.
Otrzymałeś surowy tekst z OCR. Twoim zadaniem jest:
1. Oczyścić tekst z artefaktów OCR
2. Poprawić formatowanie
3. Odpowiedzieć na pytanie użytkownika dotyczące tekstu

Bądź pomocny i zwięzły.
"""

            llm_response = await self._call_llm(
                prompt=f"Pytanie użytkownika: {message}\n\nOdczytany tekst:\n{text}",
                system_prompt=system_prompt
            )

            return f"📄 **Odczytany tekst:**\n\n{llm_response}"

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return f"❌ Błąd OCR: {str(e)}. Upewnij się, że Tesseract jest zainstalowany."

    async def _detect_objects(self, image: Image.Image, message: str) -> str:
        """Detect objects in image using AI vision model"""

        # Convert image to base64 for API
        image_base64 = await self._image_to_base64(image)

        system_prompt = """
Jesteś ekspertem od analizy obrazów.
Użytkownik pyta o obiekty na zdjęciu.

Opisz szczegółowo:
- Co widzisz na obrazie
- Jakie obiekty są obecne
- Ich położenie i relacje
- Kolory, rozmiary, ważne detale

Bądź dokładny ale naturalny w opisie.
"""

        return await self._analyze_with_vision_model(
            image, message, image_base64, system_prompt
        )

    async def _describe_scene(self, image: Image.Image, message: str) -> str:
        """Describe the scene in the image"""

        image_base64 = await self._image_to_base64(image)

        system_prompt = """
Opisz scenę na obrazie szczegółowo:
- Co się dzieje
- Kontekst i atmosfera
- Ludzie i ich aktywności (jeśli są)
- Otoczenie i tło
- Emocje i nastrój sceny

Opisuj w sposób naturalny i angażujący.
"""

        return await self._analyze_with_vision_model(
            image, message, image_base64, system_prompt
        )

    async def _analyze_with_vision_model(
        self,
        image: Image.Image,
        message: str,
        image_base64: str,
        custom_system_prompt: Optional[str] = None
    ) -> str:
        """Analyze image using OpenAI Vision API (GPT-4V)"""

        try:
            from backend.core.llm_engine import LLMEngine
            from backend.shared.config.settings import settings
            import openai

            # Initialize OpenAI client
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            system_prompt = custom_system_prompt or """
Jesteś inteligentnym asystentem z możliwością analizy obrazów.
Odpowiadaj na pytania użytkownika dotyczące obrazu w sposób:
- Dokładny i szczegółowy
- Pomocny
- Naturalny w języku
            """

            # Prepare image for API
            if not image_base64.startswith('data:image'):
                # Get image format
                img_format = image.format or 'PNG'
                mime_type = f"image/{img_format.lower()}"
                image_base64 = f"data:{mime_type};base64,{image_base64}"

            # Call GPT-4V
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Using gpt-4o-mini for vision
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": message
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_base64
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            result = response.choices[0].message.content
            return f"🔍 **Analiza obrazu:**\n\n{result}"

        except Exception as e:
            logger.error(f"Vision model error: {e}")
            return f"❌ Błąd podczas analizy AI: {str(e)}"

    async def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""

        buffered = io.BytesIO()

        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return img_str

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        vision_keywords = [
            "obraz", "zdjęcie", "foto", "screen", "screenshot",
            "co widzisz", "przeczytaj", "tekst na", "opisz zdjęcie",
            "image", "photo", "picture", "ocr", "read"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in vision_keywords if keyword in message_lower)

        # High confidence if metadata contains image
        if context.get("has_image"):
            return 0.9

        return min(matches * 0.3, 0.8)
