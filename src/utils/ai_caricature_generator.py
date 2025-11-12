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
        gemini_key: Optional[str] = None
    ):
        """
        Initialize the AI caricature generator.
        
        Args:
            provider: Preferred AI provider
            anthropic_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            openai_key: OpenAI API key (or use OPENAI_API_KEY env var)
            gemini_key: Google Gemini API key (or use GOOGLE_API_KEY env var)
        """
        self.provider = provider
        self.anthropic_key = anthropic_key or os.environ.get('ANTHROPIC_API_KEY')
        self.openai_key = openai_key or os.environ.get('OPENAI_API_KEY')
        self.gemini_key = gemini_key or os.environ.get('GOOGLE_API_KEY')
        
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
                self.anthropic_model = "claude-3-5-haiku-20241022"
                logger.info("Initialized Anthropic Claude")
                return True
                
            elif provider == AIProvider.OPENAI and self.openai_key:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
                self.openai_model = "gpt-4o-mini"  # Cost-effective vision model
                logger.info("Initialized OpenAI GPT-4V")
                return True
                
            elif provider == AIProvider.GEMINI and self.gemini_key:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Fast & affordable
                logger.info("Initialized Google Gemini")
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
        return """Analyze this image and describe how to create a simple line sketch suitable for a pen plotter - clean, bold contours with minimal detail.

IMPORTANT: The output must be a simple line drawing with:
- Clear, bold outlines only (no dense shading or crosshatching)
- Minimal interior details - only essential features
- Strong contours that define the main shapes
- Sparse lines that can be easily plotted with a single pen

Focus on identifying:
1. The 3-5 MOST distinctive features to emphasize
2. Main outline/silhouette contours only
3. Which facial features need simple bold lines (eyes, nose, mouth)
4. Hair or head shape as simple outline only
5. Avoid: dense textures, shading, fine details, or complex patterns

Provide a brief description emphasizing SIMPLICITY and CLARITY for pen plotting."""
    
    def _generate_with_anthropic(self, image: np.ndarray) -> str:
        """Generate description using Anthropic Claude."""
        image_data = self.image_to_base64(image)
        
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
    
    def _generate_with_openai(self, image: np.ndarray) -> str:
        """Generate description using OpenAI GPT-4V."""
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
        """Generate description using Google Gemini."""
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
        Apply edge detection with optional AI guidance.
        
        Args:
            image: Input image
            description: AI-generated description (optional)
            
        Returns:
            Edge-detected image with black lines on white background
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        logger.info(f"Input image: shape={gray.shape}, dtype={gray.dtype}, mean={np.mean(gray):.1f}")
        
        # Apply bilateral filter to preserve edges while smoothing noise
        smooth = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply adaptive histogram equalization for better contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(smooth)
        
        # Use moderate Canny thresholds for balanced detail
        edges = cv2.Canny(enhanced, 50, 150)
        
        logger.info(f"Edge pixels detected: {np.count_nonzero(edges)}")
        
        # Dilate slightly to make lines more visible and connected
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Close small gaps
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        logger.info(f"After morphology: {np.count_nonzero(edges)} edge pixels")
        
        # Return with black lines on white background
        result = cv2.bitwise_not(edges)
        
        logger.info(f"Final result: mean={np.mean(result):.1f}, edge pixels={np.count_nonzero(edges)}")
        
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
