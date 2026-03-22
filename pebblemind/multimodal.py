from __future__ import annotations

"""Multi-modal Capabilities for PebbleMind - Image Processing"""

import asyncio
import base64
from typing import Dict, Any, Optional, Union
from pathlib import Path
from io import BytesIO
import time

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = Any
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class ImageProcessor:
    """Lightweight image processing for multi-modal capabilities"""
    
    def __init__(self):
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")
        if not NUMPY_AVAILABLE:
            raise ImportError("NumPy is required for image processing. Install with: pip install numpy")
    
    async def process_image(self, 
                          image_input: Union[str, bytes, Path], 
                          operation: str = "describe",
                          **kwargs) -> Dict[str, Any]:
        """Process an image with the specified operation"""
        try:
            # Load image
            image = await self._load_image(image_input)
            
            # Apply the requested operation
            if operation == "describe":
                return await self._describe_image(image)
            elif operation == "resize":
                width = kwargs.get("width", 224)
                height = kwargs.get("height", 224)
                resized_image = await self._resize_image(image, width, height)
                return {
                    "status": "success",
                    "operation": "resize",
                    "result": resized_image,
                    "dimensions": f"{width}x{height}"
                }
            elif operation == "analyze_colors":
                return await self._analyze_colors(image)
            elif operation == "detect_text":
                return await self._detect_text(image)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation}",
                    "supported_operations": ["describe", "resize", "analyze_colors", "detect_text"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _load_image(self, image_input: Union[str, bytes, Path]) -> Image.Image:
        """Load an image from various input types"""
        if isinstance(image_input, (str, Path)):
            # If it's a file path
            if isinstance(image_input, str) and image_input.startswith(('http://', 'https://')):
                # For URLs, we would need to download the image
                # For now, just treat as file path
                pass
            return Image.open(image_input)
        elif isinstance(image_input, bytes):
            # If it's raw bytes
            return Image.open(BytesIO(image_input))
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")
    
    async def _describe_image(self, image: Image.Image) -> Dict[str, Any]:
        """Generate a description of the image (placeholder implementation)"""
        # Since we can't run a vision model locally without significant resources,
        # we'll return basic image properties
        width, height = image.size
        mode = image.mode
        format = image.format
        
        # If the image has EXIF data, extract relevant info
        exif_data = {}
        try:
            exif = image._getexif()
            if exif:
                # Basic EXIF tags (this is a simplified version)
                for tag, value in exif.items():
                    if tag in [271, 272]:  # Make, Model
                        tag_name = "Camera Make" if tag == 271 else "Camera Model"
                        exif_data[tag_name] = value
        except:
            pass  # Some image formats don't have EXIF data
        
        return {
            "status": "success",
            "operation": "describe",
            "image_properties": {
                "width": width,
                "height": height,
                "mode": mode,
                "format": format,
                "size_bytes": len(self._image_to_bytes(image)),
            },
            "description": f"This is an image with dimensions {width}x{height} pixels, "
                          f"in {mode} color mode, and format {format}.",
            "exif_data": exif_data if exif_data else "No EXIF data available"
        }
    
    async def _resize_image(self, image: Image.Image, width: int, height: int) -> bytes:
        """Resize an image and return as bytes"""
        resized_image = image.resize((width, height))
        return self._image_to_bytes(resized_image)
    
    async def _analyze_colors(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze dominant colors in the image"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # For efficiency, work with a smaller version
        small_image = image.resize((64, 64))
        
        # Get the pixel data
        pixels = np.array(small_image)
        pixels = pixels.reshape(-1, 3)  # Flatten to list of RGB values
        
        # Calculate average color
        avg_color = np.mean(pixels, axis=0)
        
        # Find most common colors (simplified approach)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
        most_common_idx = np.argmax(counts)
        most_common_color = unique_colors[most_common_idx]
        
        return {
            "status": "success",
            "operation": "analyze_colors",
            "average_color_rgb": [int(c) for c in avg_color],
            "most_common_color_rgb": [int(c) for c in most_common_color],
            "total_unique_colors": len(unique_colors)
        }
    
    async def _detect_text(self, image: Image.Image) -> Dict[str, Any]:
        """Detect text in image (placeholder - requires OCR library)"""
        # Since Tesseract or other OCR libraries would add substantial dependencies,
        # we'll return a message indicating what would be done
        return {
            "status": "info",
            "operation": "detect_text",
            "message": "Text detection would require an OCR library like pytesseract. "
                      "For lightweight operation, this feature is not implemented by default. "
                      "Install with: pip install pytesseract opencv-python",
            "suggestion": "For text detection in images, consider using an external service "
                         "or installing OCR capabilities separately"
        }
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert image to bytes"""
        buffer = BytesIO()
        image.save(buffer, format=image.format or 'PNG')
        return buffer.getvalue()


class MultiModalManager:
    """Manages multi-modal capabilities including image processing"""
    
    def __init__(self):
        self.image_processor: Optional[ImageProcessor] = None
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Initialize multi-modal processors if dependencies are available"""
        try:
            self.image_processor = ImageProcessor()
        except ImportError as e:
            print(f"Warning: Image processing not available: {e}")
            self.image_processor = None
    
    async def process_multimodal_input(self, 
                                     text: Optional[str] = None, 
                                     image_data: Optional[Union[str, bytes]] = None,
                                     operation: str = "analyze") -> Dict[str, Any]:
        """Process multi-modal input combining text and images"""
        results = {
            "text_analysis": text if text else "No text provided",
            "image_analysis": None,
            "combined_analysis": None,
            "timestamp": time.time()
        }
        
        if image_data and self.image_processor:
            image_result = await self.image_processor.process_image(image_data, operation)
            results["image_analysis"] = image_result
            
            # Create a combined analysis when both text and image are present
            if text:
                results["combined_analysis"] = await self._create_combined_analysis(text, image_result)
        
        elif text:
            # If only text is provided, return text analysis
            results["combined_analysis"] = text
        
        return results
    
    async def _create_combined_analysis(self, text: str, image_analysis: Dict[str, Any]) -> str:
        """Create a combined analysis from text and image data"""
        image_desc = image_analysis.get("description", "image properties")
        return f"Text: {text}\nImage: {image_desc}\nCombined: The text appears to relate to the {image_desc.split('with')[1] if 'with' in image_desc else image_desc}"
    
    def is_image_processing_available(self) -> bool:
        """Check if image processing is available"""
        return self.image_processor is not None


# Example usage functions that could be integrated into PebbleMind
async def process_image_description(image_data: Union[str, bytes], 
                                  multimodal_manager: MultiModalManager) -> str:
    """Process an image and return a description"""
    if not multimodal_manager.is_image_processing_available():
        return "Image processing is not available. Please install required dependencies (Pillow, NumPy)."
    
    result = await multimodal_manager.process_multimodal_input(
        image_data=image_data,
        operation="describe"
    )
    
    return result["image_analysis"].get("description", "Could not describe image")
