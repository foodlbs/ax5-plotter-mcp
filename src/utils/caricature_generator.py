"""
Caricature Generator using Anthropic's Claude API

This module provides AI-powered caricature generation from images using
Claude's vision capabilities.
"""

import anthropic
import base64
import os
import logging
from typing import Optional
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class CaricatureGenerator:
    """Generate caricatures from images using Anthropic's Claude API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the caricature generator.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-haiku-20241022"  # Claude 4.5 Haiku (latest as of Nov 2024)
    
    def image_to_base64(self, image: np.ndarray) -> tuple[str, str]:
        """
        Convert numpy image array to base64 string.
        
        Args:
            image: Image array (BGR format from OpenCV)
            
        Returns:
            tuple: (base64_string, media_type)
        """
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
        
        return image_data, "image/png"
    
    def generate_caricature_description(
        self,
        image: np.ndarray,
        style: str = "sketch"
    ) -> str:
        """
        Generate a text description of a caricature from an image.
        
        Args:
            image: Input image array
            style: Style of caricature (sketch, cartoon, line-art)
            
        Returns:
            str: Description of the caricature with artistic elements
        """
        image_data, media_type = self.image_to_base64(image)
        
        style_prompts = {
            "sketch": "a simple line sketch suitable for a pen plotter - clean, bold contours with minimal detail",
            "cartoon": "a cartoon-style drawing with exaggerated proportions and simplified shapes",
            "line-art": "clean line art with minimal shading, focusing on contours and key features"
        }
        
        style_desc = style_prompts.get(style, style_prompts["sketch"])
        
        prompt = f"""Analyze this image and describe how to create {style_desc} for a pen plotter.

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
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            description = message.content[0].text
            logger.info(f"Generated caricature description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate caricature description: {e}")
            raise
    
    def enhance_edges_with_ai_guidance(
        self,
        image: np.ndarray,
        description: str
    ) -> np.ndarray:
        """
        Apply edge detection with AI guidance for clean line sketches.
        
        This applies simplified edge detection optimized for pen plotting,
        producing cleaner, bolder lines with less density.
        
        Args:
            image: Input image
            description: AI-generated description (guides threshold selection)
            
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
        # Lower than before to capture more detail for caricatures
        edges = cv2.Canny(enhanced, 50, 150)
        
        logger.info(f"Edge pixels detected: {np.count_nonzero(edges)}")
        
        # Dilate slightly to make lines more visible and connected
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Close small gaps
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        logger.info(f"After morphology: {np.count_nonzero(edges)} edge pixels")
        
        # Return with black lines on white background (0 = black line, 255 = white background)
        # Invert so we have black lines on white background
        result = cv2.bitwise_not(edges)
        
        logger.info(f"Final result: mean={np.mean(result):.1f}, edge pixels={np.count_nonzero(edges)}")
        
        return result
    
    def generate_caricature(
        self,
        image: np.ndarray,
        style: str = "sketch",
        use_ai_guidance: bool = True
    ) -> tuple[np.ndarray, str]:
        """
        Generate a caricature from an input image.
        
        Args:
            image: Input image array
            style: Style of caricature
            use_ai_guidance: Whether to use AI description for guidance
            
        Returns:
            tuple: (processed_image, description)
        """
        logger.info(f"Generating caricature with style: {style}")
        
        description = ""
        if use_ai_guidance:
            try:
                description = self.generate_caricature_description(image, style)
            except Exception as e:
                logger.warning(f"AI guidance failed, using standard processing: {e}")
        
        # Apply enhanced edge detection
        processed = self.enhance_edges_with_ai_guidance(image, description)
        
        return processed, description
