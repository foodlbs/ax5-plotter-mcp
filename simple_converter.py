#!/usr/bin/env python3
"""
Simple command-line image to sketch converter for AX5 plotter.

This script provides a command-line interface to convert images to sketches
and optionally plot them directly, without needing the GUI.

Usage:
    python simple_converter.py input_image.jpg [options]

Example:
    python simple_converter.py photo.jpg --method canny --threshold1 50 --threshold2 150
    python simple_converter.py photo.jpg --method canny --plot --pen ballpoint
"""

import sys
import os
import argparse
import asyncio
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from simple_plotter_app import ImageProcessor
from src.plotter.ax5 import AX5Plotter
from src.utils.svg_converter import SVGConverter


def main():
    parser = argparse.ArgumentParser(
        description='Convert images to sketches for AX5 plotter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simple_converter.py photo.jpg
  python simple_converter.py photo.jpg --method canny --threshold1 50 --threshold2 150
  python simple_converter.py photo.jpg --output sketch.svg --plot --pen marker
        """
    )
    
    parser.add_argument('input', help='Input image file')
    parser.add_argument('--output', '-o', help='Output SVG file (default: auto-generated)')
    parser.add_argument('--method', '-m', choices=['canny', 'laplacian', 'sobel', 'contours'], 
                       default='canny', help='Edge detection method (default: canny)')
    parser.add_argument('--threshold1', '-t1', type=int, default=50, 
                       help='Lower threshold for edge detection (default: 50)')
    parser.add_argument('--threshold2', '-t2', type=int, default=150,
                       help='Upper threshold for edge detection (default: 150)')
    parser.add_argument('--blur', '-b', type=int, default=1,
                       help='Blur kernel size (default: 1)')
    parser.add_argument('--invert', action='store_true',
                       help='Invert result (white background)')
    parser.add_argument('--width', '-w', type=float, default=150,
                       help='Target width in mm (default: 150)')
    parser.add_argument('--height', '-h', type=float, default=100,
                       help='Target height in mm (default: 100)')
    parser.add_argument('--preview', '-p', action='store_true',
                       help='Show preview window')
    parser.add_argument('--plot', action='store_true',
                       help='Plot directly to AX5 plotter')
    parser.add_argument('--pen', choices=['marker', 'ballpoint', 'fountain'],
                       default='ballpoint', help='Pen profile for plotting (default: ballpoint)')
    
    args = parser.parse_args()
    
    # Check input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return 1
    
    # Load image
    print(f"Loading image: {args.input}")
    image = cv2.imread(args.input)
    if image is None:
        print(f"Error: Could not load image '{args.input}'")
        return 1
    
    print(f"Image size: {image.shape[1]}x{image.shape[0]}")
    
    # Process image
    print(f"Processing with {args.method} method...")
    processor = ImageProcessor()
    processed = processor.process_image(
        image,
        method=args.method,
        threshold1=args.threshold1,
        threshold2=args.threshold2,
        blur=args.blur,
        invert=args.invert
    )
    
    # Show preview if requested
    if args.preview:
        print("Showing preview (press any key to continue)...")
        cv2.imshow('Original', cv2.resize(image, (400, 300)))
        cv2.imshow('Processed', cv2.resize(processed, (400, 300)))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    # Generate output filename if not provided
    if args.output:
        svg_path = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        svg_path = f"{base_name}_sketch.svg"
    
    # Convert to SVG
    print(f"Converting to SVG: {svg_path}")
    processor.image_to_svg(processed, svg_path, args.width, args.height)
    print(f"SVG saved: {svg_path}")
    
    # Plot if requested
    if args.plot:
        print("Plotting to AX5 plotter...")
        
        try:
            # Convert SVG to G-code
            converter = SVGConverter()
            gcode_path = svg_path.replace('.svg', '.gcode')
            converter.convert(svg_path, gcode_path, pen_profile=args.pen)
            print(f"G-code generated: {gcode_path}")
            
            # Connect and plot
            async def plot_image():
                plotter = AX5Plotter()
                try:
                    print("Connecting to plotter...")
                    if await plotter.connect():
                        print("Connected successfully")
                        
                        print("Starting plot...")
                        def progress_callback(current, total):
                            percent = (current / total) * 100 if total > 0 else 0
                            print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end='', flush=True)
                        
                        success = await plotter.stream_gcode(gcode_path, progress_callback)
                        print()  # New line after progress
                        
                        if success:
                            print("Plot completed successfully!")
                        else:
                            print("Plot failed")
                            return 1
                    else:
                        print("Failed to connect to plotter")
                        return 1
                        
                except Exception as e:
                    print(f"Plotting error: {e}")
                    return 1
                finally:
                    await plotter.disconnect()
                
                return 0
            
            result = asyncio.run(plot_image())
            if result != 0:
                return result
            
        except Exception as e:
            print(f"Error during plotting: {e}")
            return 1
    
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())