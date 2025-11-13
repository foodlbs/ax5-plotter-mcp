"""
Multi-Provider AI Caricature Generator

Supports Anthropic Claude, OpenAI GPT-4V, and Google Gemini for AI-powered
caricature generation. Automatically falls back to Canny edge detection if
no API keys are available.
"""

import base64
import os
import logging
from typing import Optional, Tuple
from enum import Enum
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    NONE = "none"  # Fallback to Canny


class AICaricatureGenerator:
    """Generate caricatures using multiple AI providers with automatic fallback."""
    
    def __init__(
        self, 
        provider: AIProvider = AIProvider.ANTHROPIC,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        anthropic_model: str = "claude-3-5-sonnet-20241022",
        openai_model: str = "gpt-4o",
        gemini_model: str = "gemini-2.5-flash"
    ):
        """
        Initialize the AI caricature generator.
        
        Args:
            provider: Preferred AI provider
            anthropic_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            openai_key: OpenAI API key (or use OPENAI_API_KEY env var)
            gemini_key: Google Gemini API key (or use GOOGLE_API_KEY env var)
            anthropic_model: Anthropic model name
            openai_model: OpenAI model name
            gemini_model: Gemini model name
        """
        self.provider = provider
        self.anthropic_key = anthropic_key or os.environ.get('ANTHROPIC_API_KEY')
        self.openai_key = openai_key or os.environ.get('OPENAI_API_KEY')
        self.gemini_key = gemini_key or os.environ.get('GOOGLE_API_KEY')
        
        # Store model names from config
        self.anthropic_model_name = anthropic_model
        self.openai_model_name = openai_model
        self.gemini_model_name = gemini_model
        
        # Initialize clients
        self.anthropic_client = None
        self.openai_client = None
        self.gemini_model = None
        
        self._init_provider(provider)
    
    def _init_provider(self, provider: AIProvider) -> bool:
        """
        Initialize the specified provider.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if provider == AIProvider.ANTHROPIC and self.anthropic_key:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
                self.anthropic_model = self.anthropic_model_name
                logger.info(f"Initialized Anthropic Claude ({self.anthropic_model})")
                logger.info(f"Using API key starting with: {self.anthropic_key[:15]}...")
                return True
                
            elif provider == AIProvider.OPENAI and self.openai_key:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
                self.openai_model = self.openai_model_name
                logger.info(f"Initialized OpenAI ({self.openai_model})")
                return True
                
            elif provider == AIProvider.GEMINI and self.gemini_key:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                # Use the vision model for image processing
                # Note: Gemini Flash 2.0 and newer models support vision natively
                model_name = self.gemini_model_name
                # Don't append -image suffix for Gemini 2.0+ models (they have vision built-in)
                if not model_name.startswith('gemini-2.'):
                    if 'image' not in model_name and 'vision' not in model_name:
                        model_name = f"{model_name}-vision"
                self.gemini_model = genai.GenerativeModel(model_name)
                logger.info(f"Initialized Google Gemini ({model_name})")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to initialize {provider.value}: {e}")
            return False
        
        return False
    
    def get_available_providers(self) -> list[AIProvider]:
        """Get list of available AI providers based on API keys."""
        available = []
        
        if self.anthropic_key:
            available.append(AIProvider.ANTHROPIC)
        if self.openai_key:
            available.append(AIProvider.OPENAI)
        if self.gemini_key:
            available.append(AIProvider.GEMINI)
        
        # Always include fallback
        available.append(AIProvider.NONE)
        
        return available
    
    def set_provider(self, provider: AIProvider) -> bool:
        """
        Switch to a different provider.
        
        Returns:
            bool: True if switch successful
        """
        if provider == AIProvider.NONE:
            self.provider = provider
            return True
        
        if self._init_provider(provider):
            self.provider = provider
            return True
        
        return False
    
    def image_to_base64(self, image: np.ndarray) -> str:
        """Convert numpy image array to base64 string."""
        # Convert BGR to RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image)
        
        # Save to bytes buffer as PNG
        buffer = BytesIO()
        pil_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Encode to base64
        image_data = base64.b64encode(buffer.read()).decode('utf-8')
        
        return image_data
    
    def _get_ai_prompt(self) -> str:
        """Get the standardized prompt for all AI providers."""
        return """Analyze this image and create a FUNNY, EXAGGERATED caricature description for a pen plotter sketch!

MAKE IT FUNNY! Think cartoon comedy, playful exaggeration, and humorous features:
- EXAGGERATE distinctive features (big smile = HUGE grin, glasses = MASSIVE frames)
- Add playful, comedic elements to the character
- Make expressions more dramatic and funny
- Think SNL sketch character or cartoon comedy style
- Add personality and humor to the line work

The output must be a simple, HILARIOUS line drawing with:
- Clear, bold, EXAGGERATED outlines (bigger features = more fun!)
- Comedic proportions (think caricature artist at a fair)
- Strong, playful contours that emphasize funny features
- Simple lines but MAXIMUM personality

Focus on:
1. What makes this person/subject FUNNY or unique?
2. Which features can be EXAGGERATED for comedy? (big smile, wild hair, unique expression)
3. How to add humor through simple bold lines
4. Playful, cartoon-style personality
5. Keep it simple but make it LAUGH-OUT-LOUD funny

Create a description for a pen plotter that will make people smile and laugh when they see the result!"""
    
    def _generate_with_anthropic(self, image: np.ndarray) -> str:
        """Generate description using Anthropic Claude (claude-3-5-sonnet-20241022)."""
        image_data = self.image_to_base64(image)
        
        try:
            message = self.anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": self._get_ai_prompt()
                            }
                        ],
                    }
                ],
            )
            
            return message.content[0].text
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not_found_error" in error_msg:
                logger.error(f"Anthropic model '{self.anthropic_model}' not found. Your API key may not have access to this model.")
                logger.error("Please check your API key at https://console.anthropic.com/ or try a different model.")
            raise
    
    def _generate_with_openai(self, image: np.ndarray) -> str:
        """Generate description using OpenAI GPT-4o (gpt-4o)."""
        image_data = self.image_to_base64(image)
        
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._get_ai_prompt()
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024
        )
        
        return response.choices[0].message.content
    
    def _generate_with_gemini(self, image: np.ndarray) -> str:
        """Generate description using Google Gemini (gemini-2.5-flash-image)."""
        # Convert to PIL for Gemini
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image)
        
        response = self.gemini_model.generate_content([
            self._get_ai_prompt(),
            pil_image
        ])
        
        return response.text
    
    def generate_description(self, image: np.ndarray) -> Tuple[str, AIProvider]:
        """
        Generate caricature description using available AI provider.
        
        Args:
            image: Input image array
            
        Returns:
            tuple: (description, provider_used)
        """
        # Try preferred provider first
        if self.provider != AIProvider.NONE:
            try:
                if self.provider == AIProvider.ANTHROPIC and self.anthropic_client:
                    desc = self._generate_with_anthropic(image)
                    logger.info(f"Generated with Anthropic: {desc[:100]}...")
                    return desc, AIProvider.ANTHROPIC
                    
                elif self.provider == AIProvider.OPENAI and self.openai_client:
                    desc = self._generate_with_openai(image)
                    logger.info(f"Generated with OpenAI: {desc[:100]}...")
                    return desc, AIProvider.OPENAI
                    
                elif self.provider == AIProvider.GEMINI and self.gemini_model:
                    desc = self._generate_with_gemini(image)
                    logger.info(f"Generated with Gemini: {desc[:100]}...")
                    return desc, AIProvider.GEMINI
                    
            except Exception as e:
                logger.warning(f"{self.provider.value} failed: {e}, trying fallback")
        
        # Try other available providers as fallback
        available = self.get_available_providers()
        for provider in available:
            if provider != self.provider and provider != AIProvider.NONE:
                try:
                    if self.set_provider(provider):
                        return self.generate_description(image)
                except Exception as e:
                    logger.warning(f"Fallback {provider.value} failed: {e}")
                    continue
        
        # No AI available - return empty description
        logger.info("No AI providers available, using Canny fallback")
        return "", AIProvider.NONE
    
    def enhance_edges(self, image: np.ndarray, description: str = "") -> np.ndarray:
        """
        Apply edge detection with cartoon-style bold outlines.
        Creates fun, exaggerated line drawings similar to comic/cartoon style.
        
        Args:
            image: Input image
            description: AI-generated description (optional)
            
        Returns:
            Edge-detected image with black lines on white background (cartoon style)
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        logger.info(f"Input image: shape={gray.shape}, dtype={gray.dtype}, mean={np.mean(gray):.1f}")
        
        # Step 1: Reduce noise while preserving edges
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Step 2: Enhance contrast for better feature detection
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Step 3: Detect edges with multiple methods for cartoon style
        # Method 1: Canny for fine details
        edges_canny = cv2.Canny(enhanced, 30, 90)  # Higher thresholds for cleaner lines
        
        # Method 2: Laplacian for blob detection (good for features like eyes, nose)
        laplacian = cv2.Laplacian(enhanced, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        _, edges_laplacian = cv2.threshold(laplacian, 25, 255, cv2.THRESH_BINARY)
        
        # Method 3: Sobel for strong directional edges
        sobelx = cv2.Sobel(enhanced, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(enhanced, cv2.CV_64F, 0, 1, ksize=3)
        sobel_magnitude = np.sqrt(sobelx**2 + sobely**2)
        sobel_magnitude = np.uint8(sobel_magnitude)
        _, edges_sobel = cv2.threshold(sobel_magnitude, 35, 255, cv2.THRESH_BINARY)
        
        # Combine all edge detection methods for rich cartoon-style lines
        edges = cv2.bitwise_or(edges_canny, edges_laplacian)
        edges = cv2.bitwise_or(edges, edges_sobel)
        
        logger.info(f"Combined edge pixels detected: {np.count_nonzero(edges)}")
        
        # Step 4: Clean up and thin the lines
        # Use smaller kernel for cleaner, thinner lines
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_clean, iterations=1)
        
        # Thin the lines using morphological thinning
        # This creates single-pixel width lines
        kernel_thin = np.ones((3, 3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_thin, iterations=1)
        
        # Optional: slight dilation for visibility (much less than before)
        kernel_slight = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        edges = cv2.dilate(edges, kernel_slight, iterations=1)
        
        logger.info(f"After thinning: {np.count_nonzero(edges)} edge pixels")
        
        # Return with black lines on white background (classic cartoon style)
        result = cv2.bitwise_not(edges)
        
        logger.info(f"Final cartoon result: mean={np.mean(result):.1f}, edge pixels={np.count_nonzero(edges)}")
        
        return result
    
    def generate_caricature(
        self,
        image: np.ndarray
    ) -> Tuple[np.ndarray, str, AIProvider]:
        """
        Generate a caricature from an input image.
        
        Args:
            image: Input image array
            
        Returns:
            tuple: (processed_image, description, provider_used)
        """
        logger.info(f"Generating caricature with provider: {self.provider.value}")
        
        # Try to get AI description
        description, provider_used = self.generate_description(image)
        
        # Apply edge detection
        processed = self.enhance_edges(image, description)
        
        return processed, description, provider_used
