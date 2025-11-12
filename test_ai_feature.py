#!/usr/bin/env python3
"""
Quick test script for AI caricature feature.

Tests:
1. Import check
2. API key detection
3. Simple image processing (if key available)

Usage:
    export ANTHROPIC_API_KEY='your-key-here'
    python3 test_ai_feature.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        from src.utils.caricature_generator import CaricatureGenerator
        print("✓ CaricatureGenerator imported successfully")
        
        import anthropic
        print(f"✓ anthropic package imported (version: {anthropic.__version__})")
        
        import cv2
        import numpy as np
        print("✓ OpenCV and NumPy available")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_api_key():
    """Test if API key is configured."""
    print("\nTesting API key configuration...")
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not set")
        print("  Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return False
    
    if api_key.startswith('sk-ant-api'):
        print(f"✓ API key found (starts with: {api_key[:15]}...)")
        return True
    else:
        print("⚠ API key found but format looks unusual")
        print(f"  Expected to start with 'sk-ant-api', got: {api_key[:15]}...")
        return True


def test_generator_init():
    """Test that CaricatureGenerator can be initialized."""
    print("\nTesting CaricatureGenerator initialization...")
    try:
        from src.utils.caricature_generator import CaricatureGenerator
        
        generator = CaricatureGenerator()
        print("✓ CaricatureGenerator instance created")
        
        if generator.client:
            print("✓ Anthropic client initialized")
            return True
        else:
            print("✗ Anthropic client is None")
            return False
            
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False


def test_with_sample_image():
    """Test caricature generation with a simple test image."""
    print("\nTesting caricature generation with sample image...")
    
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("⊘ Skipping (no API key)")
        return None
    
    try:
        import cv2
        import numpy as np
        from src.utils.caricature_generator import CaricatureGenerator
        
        # Create a simple test image (gradient)
        test_image = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.circle(test_image, (100, 100), 50, (255, 255, 255), -1)
        cv2.circle(test_image, (80, 80), 10, (0, 0, 0), -1)
        cv2.circle(test_image, (120, 80), 10, (0, 0, 0), -1)
        cv2.ellipse(test_image, (100, 120), (30, 15), 0, 0, 180, (0, 0, 0), 2)
        
        print("✓ Created 200x200 test image (simple face)")
        
        generator = CaricatureGenerator()
        print("✓ Generator initialized")
        
        print("  Calling API (this may take 3-5 seconds)...")
        processed, description = generator.generate_caricature(test_image, style="sketch")
        
        if processed is not None:
            print(f"✓ Caricature generated successfully")
            print(f"  Output shape: {processed.shape}")
            print(f"  AI description: {description[:100]}..." if len(description) > 100 else f"  AI description: {description}")
            return True
        else:
            print("✗ Caricature generation returned None")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AI Caricature Feature Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: API Key
    api_key_ok = test_api_key()
    results.append(("API Key", api_key_ok))
    
    # Test 3: Generator init
    if results[0][1]:  # Only if imports worked
        results.append(("Generator Init", test_generator_init()))
    
    # Test 4: Sample generation (optional - only if API key exists)
    if api_key_ok and results[0][1]:
        result = test_with_sample_image()
        if result is not None:
            results.append(("Sample Generation", result))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    # Overall result
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        print("\nYou're ready to use AI caricature mode!")
        return 0
    elif passed > 0:
        print(f"⚠ PARTIAL SUCCESS ({passed}/{total})")
        if not api_key_ok:
            print("\nTo enable full functionality:")
            print("1. Get API key from https://console.anthropic.com/")
            print("2. export ANTHROPIC_API_KEY='your-key-here'")
            print("3. Re-run this test")
        return 1
    else:
        print(f"✗ TESTS FAILED ({passed}/{total})")
        print("\nPlease check the errors above and:")
        print("1. Ensure all packages are installed: pip install -r requirements-simple.txt")
        print("2. Check that src/utils/caricature_generator.py exists")
        return 2


if __name__ == "__main__":
    sys.exit(main())
