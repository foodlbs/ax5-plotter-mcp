"""
Basic test script for AX5 plotter functionality.
Run this to verify your setup is working correctly.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.plotter.ax5 import AX5Plotter
from src.utils.svg_converter import SVGConverter


async def test_connection():
    """Test basic plotter connection."""
    print("Testing plotter connection...")
    
    plotter = AX5Plotter()
    
    try:
        connected = await plotter.connect()
        
        if connected:
            print("✓ Successfully connected to plotter")
            
            # Get status
            status = await plotter.get_status()
            print(f"✓ Plotter state: {status['state']}")
            print(f"  Position: X{status['position']['x']:.2f} Y{status['position']['y']:.2f}")
            
            return True
        else:
            print("✗ Failed to connect to plotter")
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False
    finally:
        await plotter.disconnect()


async def test_pen_control():
    """Test pen up/down control."""
    print("\nTesting pen control...")
    
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        
        # Test pen down
        print("Lowering pen...")
        await plotter.pen_control(down=True)
        await asyncio.sleep(0.5)
        print("✓ Pen down")
        
        # Test pen up
        print("Raising pen...")
        await plotter.pen_control(down=False)
        await asyncio.sleep(0.5)
        print("✓ Pen up")
        
        return True
        
    except Exception as e:
        print(f"✗ Pen control error: {e}")
        return False
    finally:
        await plotter.disconnect()


async def test_movement():
    """Test basic movement."""
    print("\nTesting movement...")
    
    plotter = AX5Plotter()
    
    try:
        await plotter.connect()
        
        # Move to known position
        print("Moving to (10, 10)...")
        await plotter.move_to(10, 10)
        print("✓ Movement command sent")
        
        await asyncio.sleep(1)
        
        # Return to origin
        print("Returning to origin...")
        await plotter.move_to(0, 0)
        print("✓ Returned to origin")
        
        return True
        
    except Exception as e:
        print(f"✗ Movement error: {e}")
        return False
    finally:
        await plotter.disconnect()


def test_svg_converter():
    """Test SVG conversion (without plotter)."""
    print("\nTesting SVG converter...")
    
    # Create a simple test SVG
    test_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="10" width="80" height="80" fill="none" stroke="black"/>
</svg>"""
    
    test_file = "test_square.svg"
    
    try:
        # Write test SVG
        with open(test_file, 'w') as f:
            f.write(test_svg)
        
        # Convert
        converter = SVGConverter()
        gcode_file = converter.convert(test_file, optimize=False)
        
        # Check output
        if os.path.exists(gcode_file):
            print(f"✓ G-code generated: {gcode_file}")
            
            # Read and display first few lines
            with open(gcode_file, 'r') as f:
                lines = f.readlines()[:5]
                print("  First 5 lines:")
                for line in lines:
                    print(f"    {line.strip()}")
            
            return True
        else:
            print("✗ G-code file not created")
            return False
            
    except Exception as e:
        print(f"✗ SVG conversion error: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


async def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("AX5 Plotter Test Suite")
    print("=" * 50)
    
    results = {}
    
    # Test 1: Connection
    results['connection'] = await test_connection()
    
    # Test 2: Pen control (only if connected)
    if results['connection']:
        results['pen_control'] = await test_pen_control()
    
    # Test 3: Movement (only if connected)
    if results['connection']:
        results['movement'] = await test_movement()
    
    # Test 4: SVG converter (standalone)
    results['svg_converter'] = test_svg_converter()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20} {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
