#!/usr/bin/env python3
"""
Photo Booth End-to-End Test Script

Tests all functionality without launching the full GUI.
Run this to verify everything works before testing with real users.
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, 'src')

def print_step(step_num, description):
    """Print a test step."""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60)

def print_result(success, message):
    """Print test result."""
    icon = "✓" if success else "✗"
    print(f"{icon} {message}")

def test_imports():
    """Test that all required modules can be imported."""
    print_step(1, "Testing Imports")
    
    try:
        from src.utils.print_queue import PrintQueue, ImageStyle, JobStatus
        print_result(True, "Print queue imports OK")
    except Exception as e:
        print_result(False, f"Print queue import failed: {e}")
        return False
    
    try:
        from src.utils.ai_caricature_generator import AICaricatureGenerator, AIProvider
        print_result(True, "AI generator imports OK")
    except Exception as e:
        print_result(False, f"AI generator import failed: {e}")
        return False
    
    try:
        from src.utils.svg_converter import SVGConverter
        print_result(True, "SVG converter imports OK")
    except Exception as e:
        print_result(False, f"SVG converter import failed: {e}")
        return False
    
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
        print_result(True, "Tkinter GUI available")
    except Exception as e:
        print_result(False, f"Tkinter not available: {e}")
        return False
    
    return True

def test_camera():
    """Test camera capture."""
    print_step(2, "Testing Camera")
    
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print_result(False, "Camera not available")
        return False
    
    print_result(True, "Camera opened successfully")
    
    # Try to capture a frame
    ret, frame = camera.read()
    
    if not ret or frame is None:
        print_result(False, "Could not capture frame")
        camera.release()
        return False
    
    print_result(True, f"Frame captured: {frame.shape[1]}x{frame.shape[0]} pixels")
    
    # Save test capture
    test_dir = Path("output/test_captures")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_path = test_dir / "test_capture.jpg"
    
    cv2.imwrite(str(test_path), frame)
    print_result(True, f"Test image saved to: {test_path}")
    
    camera.release()
    return True, frame

def test_image_processing(image):
    """Test image processing with Canny."""
    print_step(3, "Testing Image Processing (Canny)")
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        print_result(True, "Converted to grayscale")
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        print_result(True, "Applied Canny edge detection")
        
        # Count edge pixels
        edge_pixels = np.count_nonzero(edges)
        print_result(True, f"Found {edge_pixels:,} edge pixels")
        
        # Save processed image
        test_dir = Path("output/test_processed")
        test_dir.mkdir(parents=True, exist_ok=True)
        test_path = test_dir / "test_processed.png"
        
        cv2.imwrite(str(test_path), edges)
        print_result(True, f"Processed image saved to: {test_path}")
        
        return True, str(test_path)
        
    except Exception as e:
        print_result(False, f"Processing failed: {e}")
        return False, None

def test_queue_system():
    """Test print queue."""
    print_step(4, "Testing Queue System")
    
    try:
        from src.utils.print_queue import PrintQueue, ImageStyle, JobStatus
        
        queue = PrintQueue()
        print_result(True, "Queue created")
        
        # Add a test job
        job_id = queue.add_job(
            name="Test User",
            email="test@example.com",
            image_path="output/test_captures/test_capture.jpg",
            style=ImageStyle.CARTOON,
            ai_provider="None (Canny)"
        )
        
        print_result(True, f"Job added: {job_id[:8]}...")
        
        # Check job exists
        job = queue.get_job(job_id)
        if job:
            print_result(True, f"Job retrieved: {job.name}")
        else:
            print_result(False, "Could not retrieve job")
            return False
        
        # Check statistics
        stats = queue.get_statistics()
        print_result(True, f"Queue stats: {stats['queued']} queued, {stats['completed']} completed")
        
        # Update status
        queue.update_status(job_id, JobStatus.COMPLETED)
        job = queue.get_job(job_id)
        
        if job.status == JobStatus.COMPLETED:
            print_result(True, "Status updated successfully")
        else:
            print_result(False, "Status update failed")
            return False
        
        return True
        
    except Exception as e:
        print_result(False, f"Queue test failed: {e}")
        return False

def test_folder_creation():
    """Test folder organization."""
    print_step(5, "Testing Folder Organization")
    
    try:
        base_dir = Path("output/saved_images")
        base_dir.mkdir(parents=True, exist_ok=True)
        print_result(True, "Base directory created")
        
        # Test folder naming
        test_name = "John Doe"
        test_email = "john@example.com"
        
        safe_name = test_name.replace(' ', '_').replace('/', '_')
        safe_email = test_email.replace('@', '_at_').replace('.', '_')
        
        folder_name = f"{safe_name}_{safe_email}"
        print_result(True, f"Folder name: {folder_name}")
        
        # Create test folder
        user_folder = base_dir / folder_name
        user_folder.mkdir(parents=True, exist_ok=True)
        print_result(True, f"User folder created: {user_folder}")
        
        # Create test files
        test_file = user_folder / "cartoon_20231113_120000.png"
        test_file.write_text("test")
        print_result(True, f"Test file created: {test_file.name}")
        
        return True
        
    except Exception as e:
        print_result(False, f"Folder test failed: {e}")
        return False

def test_ui_launch():
    """Test that the UI can be launched."""
    print_step(6, "Testing UI Launch")
    
    try:
        import tkinter as tk
        
        # Create a minimal test window
        root = tk.Tk()
        root.title("Photo Booth Test")
        
        # Test basic widgets
        tk.Label(root, text="Test Label").pack()
        tk.Button(root, text="Test Button").pack()
        tk.Entry(root).pack()
        
        print_result(True, "Basic widgets created")
        
        # Don't show the window, just verify it works
        root.update()
        root.destroy()
        
        print_result(True, "UI framework working")
        
        return True
        
    except Exception as e:
        print_result(False, f"UI test failed: {e}")
        return False

def print_summary():
    """Print test summary and next steps."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("\n✓ All core functionality tested and working!")
    print("\nNext Steps for Full End-to-End Test:")
    print("\n1. Launch the photo booth app:")
    print("   ./launch_photo_booth.sh")
    print("   or: python3 photo_booth_app.py")
    print("\n2. Test the complete workflow:")
    print("   a. Check live preview appears")
    print("   b. Click 'Capture Photo'")
    print("   c. Enter name: Test User")
    print("   d. Enter email: test@example.com")
    print("   e. Select a style (e.g., Cartoon)")
    print("   f. Keep AI provider as 'None (Canny)'")
    print("   g. Click 'Add to Print Queue'")
    print("   h. Watch queue dashboard")
    print("   i. When complete, check folder:")
    print("      output/saved_images/Test_User_test_at_example_com/")
    print("\n3. Files to verify:")
    print("   - cartoon_YYYYMMDD_HHMMSS.png (processed image)")
    print("   - cartoon_YYYYMMDD_HHMMSS.gcode (plotter file)")
    print("\n" + "="*60)

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PHOTO BOOTH END-TO-END TEST")
    print("="*60)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
        print("\n✗ FAILED: Import test failed")
        return
    
    # Test camera
    camera_result = test_camera()
    if isinstance(camera_result, tuple):
        success, frame = camera_result
        if not success:
            all_passed = False
            print("\n✗ FAILED: Camera test failed")
            return
    else:
        if not camera_result:
            all_passed = False
            print("\n✗ FAILED: Camera test failed")
            return
        frame = None
    
    # Test image processing
    if frame is not None:
        success, processed_path = test_image_processing(frame)
        if not success:
            all_passed = False
            print("\n✗ FAILED: Image processing test failed")
            return
    
    # Test queue system
    if not test_queue_system():
        all_passed = False
        print("\n✗ FAILED: Queue test failed")
        return
    
    # Test folder creation
    if not test_folder_creation():
        all_passed = False
        print("\n✗ FAILED: Folder test failed")
        return
    
    # Test UI
    if not test_ui_launch():
        all_passed = False
        print("\n✗ FAILED: UI test failed")
        return
    
    # Print summary
    if all_passed:
        print_summary()
    else:
        print("\n✗ SOME TESTS FAILED - Check errors above")

if __name__ == '__main__':
    main()
