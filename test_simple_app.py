#!/usr/bin/env python3
"""
Test script for the Simple AX5 Plotter Application.

This script tests various components of the simple plotter app without
requiring a physical plotter connection.

Usage:
    python test_simple_app.py
"""

import sys
import os
import tempfile
import numpy as np
import cv2
from PIL import Image

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from simple_plotter_app import ImageProcessor, WebcamCapture
    print("✓ Successfully imported simple_plotter_app components")
except ImportError as e:
    print(f"✗ Failed to import simple_plotter_app: {e}")
    sys.exit(1)


def create_test_image(width=400, height=300):
    """Create a simple test image with geometric shapes."""
    # Create white background
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Add some shapes for edge detection
    # Rectangle
    cv2.rectangle(img, (50, 50), (150, 120), (0, 0, 0), 2)
    
    # Circle
    cv2.circle(img, (250, 100), 40, (0, 0, 0), 2)
    
    # Triangle
    pts = np.array([[300, 200], [350, 100], [400, 200]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(img, [pts], True, (0, 0, 0), 2)
    
    # Add some text
    cv2.putText(img, 'TEST', (100, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    
    return img


def test_image_processor():
    """Test the ImageProcessor class."""
    print("\n=== Testing ImageProcessor ===")
    
    processor = ImageProcessor()
    
    # Test methods list
    print(f"Available methods: {list(processor.methods.keys())}")
    
    # Create test image
    test_img = create_test_image()
    print(f"Created test image: {test_img.shape}")
    
    # Test each processing method
    for method in processor.methods.keys():
        try:
            processed = processor.process_image(
                test_img, 
                method=method,
                threshold1=50,
                threshold2=150,
                blur=1,
                invert=True
            )
            print(f"✓ {method} method: output shape {processed.shape}")
        except Exception as e:
            print(f"✗ {method} method failed: {e}")
    
    # Test SVG conversion
    try:
        processed = processor.process_image(test_img, method='canny')
        
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp:
            svg_path = tmp.name
        
        processor.image_to_svg(processed, svg_path, width_mm=100, height_mm=80)
        
        # Check if SVG was created and has content
        if os.path.exists(svg_path):
            with open(svg_path, 'r') as f:
                content = f.read()
            if len(content) > 0 and 'svg' in content:
                print(f"✓ SVG conversion successful: {len(content)} characters")
            else:
                print("✗ SVG conversion created empty file")
            os.unlink(svg_path)
        else:
            print("✗ SVG conversion failed to create file")
            
    except Exception as e:
        print(f"✗ SVG conversion failed: {e}")


def test_webcam_mock():
    """Test webcam functionality (without actual camera)."""
    print("\n=== Testing WebcamCapture (Mock) ===")
    
    webcam = WebcamCapture()
    
    # Test that webcam functions exist and handle errors gracefully
    try:
        # This should fail gracefully since no camera is connected
        result = webcam.start_capture(camera_index=99)  # Non-existent camera
        print(f"Start capture (should fail): {result}")
        
        # Test other methods
        frame = webcam.get_frame()
        print(f"Get frame (should be None): {frame is None}")
        
        capture = webcam.capture_image()
        print(f"Capture image (should be None): {capture is None}")
        
        webcam.stop_capture()
        print("✓ Webcam methods work correctly")
        
    except Exception as e:
        print(f"✗ Webcam test failed: {e}")


def test_config_loading():
    """Test configuration file loading."""
    print("\n=== Testing Configuration ===")
    
    config_files = [
        "config/settings.yaml",
        "config/settings.example.yaml"
    ]
    
    config_found = False
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✓ Found config file: {config_file}")
            config_found = True
            
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check for required sections
                required_sections = ['plotter', 'servo', 'speeds']
                for section in required_sections:
                    if section in config:
                        print(f"  ✓ Section '{section}' found")
                    else:
                        print(f"  ✗ Section '{section}' missing")
                        
            except Exception as e:
                print(f"  ✗ Failed to load config: {e}")
    
    if not config_found:
        print("✗ No configuration files found")


def test_imports():
    """Test all required imports."""
    print("\n=== Testing Imports ===")
    
    imports_to_test = [
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('PIL', 'Pillow'),
        ('yaml', 'PyYAML'),
        ('tkinter', 'Tkinter (GUI)'),
    ]
    
    for module, name in imports_to_test:
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError as e:
            print(f"✗ {name}: {e}")


def test_file_structure():
    """Test that required files and directories exist."""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        'simple_plotter_app.py',
        'simple_converter.py',
        'requirements-simple.txt',
        'launch_simple_app.sh',
        'launch_simple_app.bat'
    ]
    
    required_dirs = [
        'src',
        'src/plotter',
        'src/utils',
        'config'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ (missing)")


def test_image_formats():
    """Test support for different image formats."""
    print("\n=== Testing Image Format Support ===")
    
    # Create test images in different formats
    test_img = create_test_image(200, 150)
    
    formats_to_test = [
        ('.jpg', 'JPEG'),
        ('.png', 'PNG'),
        ('.bmp', 'BMP'),
    ]
    
    temp_dir = tempfile.mkdtemp()
    processor = ImageProcessor()
    
    for ext, format_name in formats_to_test:
        try:
            # Save test image
            test_path = os.path.join(temp_dir, f"test{ext}")
            if ext == '.jpg':
                cv2.imwrite(test_path, test_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            else:
                cv2.imwrite(test_path, test_img)
            
            # Try to load and process
            loaded = cv2.imread(test_path)
            if loaded is not None:
                processed = processor.process_image(loaded, method='canny')
                print(f"✓ {format_name} format")
            else:
                print(f"✗ {format_name} format (load failed)")
                
        except Exception as e:
            print(f"✗ {format_name} format: {e}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    print("Simple AX5 Plotter Application Test Suite")
    print("=========================================")
    
    # Run all tests
    test_imports()
    test_file_structure()
    test_config_loading()
    test_image_processor()
    test_webcam_mock()
    test_image_formats()
    
    print("\n=== Test Summary ===")
    print("Tests completed. Check output above for any ✗ (failed) items.")
    print("\nTo run the full application:")
    print("  ./launch_simple_app.sh      (Linux/macOS)")
    print("  launch_simple_app.bat       (Windows)")
    print("  python simple_plotter_app.py")
    print("\nTo test image conversion:")
    print("  python simple_converter.py test_image.jpg --preview")


if __name__ == "__main__":
    main()