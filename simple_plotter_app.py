#!/usr/bin/env python3
"""
AX5 Plotter Simple Local Application

A simple GUI application for converting images to sketches and plotting them
on the AX5 plotter. Supports file upload, webcam capture, and various
image processing options.

Usage:
    python simple_plotter_app.py

Requirements:
    - AX5 plotter connected via USB
    - Settings file configured (config/settings.yaml)
    - Python packages: see requirements-simple.txt
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import os
import sys
import asyncio
import threading
import logging
from PIL import Image, ImageTk
from typing import Optional, Callable
import tempfile
import yaml

# Add src to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.plotter.ax5 import AX5Plotter
from src.utils.svg_converter import SVGConverter
from src.utils.ai_caricature_generator import AICaricatureGenerator, AIProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing for sketch conversion."""
    
    def __init__(self):
        self.methods = {
            'canny': 'Canny Edge Detection',
            'laplacian': 'Laplacian Edge Detection',
            'sobel': 'Sobel Edge Detection',
            'contours': 'Contour Detection'
        }
    
    def process_image(
        self,
        image: np.ndarray,
        method: str = 'canny',
        threshold1: int = 50,
        threshold2: int = 150,
        blur: int = 1,
        invert: bool = True
    ) -> np.ndarray:
        """
        Convert image to sketch using edge detection.
        
        Args:
            image: Input image array
            method: Edge detection method
            threshold1: Lower threshold for edge detection
            threshold2: Upper threshold for edge detection
            blur: Blur kernel size (odd numbers only)
            invert: Whether to invert the result
            
        Returns:
            np.ndarray: Processed sketch image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply blur if specified
        if blur > 1:
            if blur % 2 == 0:
                blur += 1  # Make odd
            gray = cv2.GaussianBlur(gray, (blur, blur), 0)
        
        # Apply edge detection
        if method == 'canny':
            edges = cv2.Canny(gray, threshold1, threshold2)
        elif method == 'laplacian':
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.uint8(np.absolute(edges))
        elif method == 'sobel':
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobelx**2 + sobely**2)
            edges = np.uint8(edges)
        elif method == 'contours':
            # Use adaptive threshold for contours
            edges = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        else:
            edges = gray
        
        # Invert if requested (for white background)
        if invert and method != 'contours':
            edges = cv2.bitwise_not(edges)
        
        return edges
    
    def image_to_svg(
        self, 
        image: np.ndarray, 
        output_path: str,
        width_mm: float = 150,
        height_mm: float = 150
    ) -> str:
        """
        Convert processed image to SVG format.
        
        Args:
            image: Processed image array (should be binary with black lines)
            output_path: Path to save SVG
            width_mm: Target width in mm
            height_mm: Target height in mm
            
        Returns:
            str: Path to created SVG file
        """
        # Ensure image is binary
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        logger.info(f"Image shape: {image.shape}, dtype: {image.dtype}, mean: {np.mean(image):.1f}")
        
        # Check if image needs inversion (white background should have high values)
        # If mean is low, image likely has white lines on black background - invert it
        if np.mean(image) < 127:
            logger.info("Inverting image (detected white lines on black background)")
            image = cv2.bitwise_not(image)
        
        # Apply threshold to ensure clean binary image
        _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        
        # Invert for contour detection (findContours expects white objects on black background)
        inverted = cv2.bitwise_not(binary)
        
        logger.info(f"Binary image mean: {np.mean(binary):.1f}, non-zero pixels: {np.count_nonzero(inverted)}")
        
        # Find contours - use RETR_LIST to get all contours
        contours, _ = cv2.findContours(
            inverted, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        
        logger.info(f"Found {len(contours)} contours in image")
        
        # Filter out very small contours (noise)
        min_contour_area = 10  # pixels
        contours = [c for c in contours if cv2.contourArea(c) > min_contour_area]
        
        logger.info(f"Using {len(contours)} contours after filtering")
        
        # Create SVG content
        svg_content = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" ',
            f'width="{width_mm}mm" height="{height_mm}mm" ',
            f'viewBox="0 0 {image.shape[1]} {image.shape[0]}">',
        ]
        
        # Scale factors
        x_scale = width_mm / image.shape[1]
        y_scale = height_mm / image.shape[0]
        
        # Convert contours to SVG paths
        for contour in contours:
            if len(contour) > 2:  # Skip tiny contours
                # Approximate contour to reduce points
                epsilon = 0.005 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) > 2:
                    path_data = []
                    for i, point in enumerate(approx):
                        x, y = point[0]
                        # Scale to mm
                        x_mm = x * x_scale
                        y_mm = y * y_scale
                        
                        if i == 0:
                            path_data.append(f"M {x_mm:.2f} {y_mm:.2f}")
                        else:
                            path_data.append(f"L {x_mm:.2f} {y_mm:.2f}")
                    
                    # Close path if it's a contour
                    if len(approx) > 3:
                        path_data.append("Z")
                    
                    path_string = " ".join(path_data)
                    svg_content.append(
                        f'  <path d="{path_string}" '
                        f'fill="none" stroke="black" stroke-width="0.1"/>'
                    )
        
        svg_content.append('</svg>')
        
        # Write SVG file
        with open(output_path, 'w') as f:
            f.write('\n'.join(svg_content))
        
        logger.info(f"Created SVG with {len(contours)} contours: {output_path}")
        return output_path


class WebcamCapture:
    """Webcam capture functionality."""
    
    def __init__(self):
        self.cap = None
        self.is_capturing = False
    
    def start_capture(self, camera_index: int = 0) -> bool:
        """Start webcam capture."""
        try:
            # List of camera indices and backends to try
            attempts = [
                (camera_index, None),  # Default backend
                (0, None),
                (1, None),
                (0, cv2.CAP_AVFOUNDATION),  # macOS AVFoundation backend
                (1, cv2.CAP_AVFOUNDATION),
                (0, cv2.CAP_ANY),  # Auto-detect backend
            ]
            
            success = False
            for idx, backend in attempts:
                try:
                    if backend is not None:
                        logger.info(f"Trying camera index {idx} with backend {backend}")
                        self.cap = cv2.VideoCapture(idx, backend)
                    else:
                        logger.info(f"Trying camera index {idx} with default backend")
                        self.cap = cv2.VideoCapture(idx)
                    
                    # Give it a moment to initialize
                    import time
                    time.sleep(0.5)
                    
                    if self.cap.isOpened():
                        # Try to read a test frame
                        ret, frame = self.cap.read()
                        if ret and frame is not None:
                            logger.info(f"✓ Successfully opened camera at index {idx}" + 
                                      (f" with backend {backend}" if backend else ""))
                            success = True
                            break
                        else:
                            logger.warning(f"Camera {idx} opened but couldn't read frame")
                            self.cap.release()
                    else:
                        self.cap.release()
                        
                except Exception as e:
                    logger.debug(f"Failed attempt with index {idx}: {e}")
                    if self.cap:
                        self.cap.release()
                    continue
            
            if not success:
                logger.error("=" * 60)
                logger.error("CAMERA INITIALIZATION FAILED")
                logger.error("=" * 60)
                logger.error("")
                logger.error("Common issues on macOS:")
                logger.error("")
                logger.error("1. CAMERA PERMISSIONS NOT GRANTED:")
                logger.error("   → Go to: System Settings > Privacy & Security > Camera")
                logger.error("   → Enable camera access for 'Terminal' or 'Python'")
                logger.error("   → You may need to restart the application")
                logger.error("")
                logger.error("2. NO CAMERA CONNECTED:")
                logger.error("   → Check if a camera is physically connected")
                logger.error("   → For built-in cameras, check if camera is working in other apps")
                logger.error("   → For USB cameras, try unplugging and reconnecting")
                logger.error("")
                logger.error("3. CAMERA IN USE BY ANOTHER APP:")
                logger.error("   → Close Zoom, FaceTime, Photo Booth, etc.")
                logger.error("   → Check Activity Monitor for apps using the camera")
                logger.error("")
                logger.error("=" * 60)
                return False
            
            # Set resolution for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.is_capturing = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to start webcam: {e}")
            return False
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame from webcam."""
        if self.cap and self.is_capturing:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    def capture_image(self) -> Optional[np.ndarray]:
        """Capture current frame as image."""
        frame = self.get_frame()
        if frame is not None:
            return frame.copy()
        return None
    
    def stop_capture(self):
        """Stop webcam capture."""
        self.is_capturing = False
        if self.cap:
            self.cap.release()
            self.cap = None


class SimplePlotterApp:
    """Simple AX5 Plotter Application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AX5 Plotter - Simple Local App")
        self.root.geometry("800x700")
        
        # Initialize components
        self.image_processor = ImageProcessor()
        self.webcam = WebcamCapture()
        self.plotter = None
        self.svg_converter = None
        self.ai_generator = None  # Initialize on first use
        
        # State variables
        self.current_image = None
        self.processed_image = None
        self.current_svg_path = None
        self.current_gcode_path = None
        self.temp_dir = tempfile.mkdtemp()
        
        # API keys (stored in memory)
        self.anthropic_api_key = None
        self.openai_api_key = None
        self.gemini_api_key = None
        
        # Load configuration
        self.load_config()
        
        # Initialize GUI
        self.setup_gui()
        
        # Webcam update loop
        self.webcam_active = False
        self.update_webcam()
    
    def load_config(self):
        """Load plotter configuration."""
        config_path = "config/settings.yaml"
        if not os.path.exists(config_path):
            # Try example config
            config_path = "config/settings.example.yaml"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.config = None
        else:
            logger.warning("No configuration file found")
            self.config = None
    
    def setup_gui(self):
        """Setup the GUI components."""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image input tab
        self.input_frame = ttk.Frame(notebook)
        notebook.add(self.input_frame, text="Image Input")
        self.setup_input_tab()
        
        # Processing tab
        self.process_frame = ttk.Frame(notebook)
        notebook.add(self.process_frame, text="Image Processing")
        self.setup_processing_tab()
        
        # Plotter tab
        self.plotter_frame = ttk.Frame(notebook)
        notebook.add(self.plotter_frame, text="Plotter Control")
        self.setup_plotter_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_input_tab(self):
        """Setup image input tab."""
        # File input section
        file_frame = ttk.LabelFrame(self.input_frame, text="File Input", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            file_frame, text="Select Image File", 
            command=self.select_file
        ).pack(side=tk.LEFT, padx=5)
        
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # Webcam section
        webcam_frame = ttk.LabelFrame(self.input_frame, text="Webcam Input", padding=10)
        webcam_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.webcam_button = ttk.Button(
            webcam_frame, text="Start Webcam", 
            command=self.toggle_webcam
        )
        self.webcam_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            webcam_frame, text="Capture Image", 
            command=self.capture_webcam_image
        ).pack(side=tk.LEFT, padx=5)
        
        # Image preview
        preview_frame = ttk.LabelFrame(self.input_frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = ttk.Label(preview_frame)
        self.image_label.pack(expand=True)
    
    def setup_processing_tab(self):
        """Setup image processing tab - simplified with AI provider selection."""
        # Processing controls
        controls_frame = ttk.LabelFrame(self.process_frame, text="Processing Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # AI Provider selection
        ttk.Label(controls_frame, text="AI Provider:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ai_provider_var = tk.StringVar(value="None (Canny)")
        self.ai_provider_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.ai_provider_var,
            values=["None (Canny)", "Anthropic Claude", "OpenAI GPT-4V", "Google Gemini"],
            state='readonly',
            width=20
        )
        self.ai_provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.ai_provider_combo.bind('<<ComboboxSelected>>', self.on_provider_changed)
        
        # API Keys button
        ttk.Button(
            controls_frame, text="⚙️ Configure API Keys",
            command=self.configure_api_keys,
            width=20
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Process button
        ttk.Button(
            controls_frame, text="Process Image",
            command=self.process_current_image,
            width=20
        ).grid(row=2, column=0, columnspan=2, pady=10)
        
        # G-code conversion section
        gcode_frame = ttk.LabelFrame(self.process_frame, text="G-code Generation", padding=10)
        gcode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            gcode_frame, text="Generate G-code",
            command=self.generate_gcode
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            gcode_frame, text="View G-code",
            command=self.view_gcode
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            gcode_frame, text="Save G-code As...",
            command=self.save_gcode
        ).pack(side=tk.LEFT, padx=5)
        
        self.gcode_status = ttk.Label(gcode_frame, text="No G-code generated")
        self.gcode_status.pack(side=tk.LEFT, padx=10)
        
        # Result preview
        result_frame = ttk.LabelFrame(self.process_frame, text="Processed Result", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.result_label = ttk.Label(result_frame)
        self.result_label.pack(expand=True)
    
    def setup_plotter_tab(self):
        """Setup plotter control tab."""
        # Connection section
        conn_frame = ttk.LabelFrame(self.plotter_frame, text="Plotter Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.connect_button = ttk.Button(
            conn_frame, text="Connect Plotter",
            command=self.connect_plotter
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.plotter_status = ttk.Label(conn_frame, text="Disconnected")
        self.plotter_status.pack(side=tk.LEFT, padx=10)
        
        # Control buttons
        control_frame = ttk.LabelFrame(self.plotter_frame, text="Plotter Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            control_frame, text="Home Plotter",
            command=self.home_plotter
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, text="Test Pen Up",
            command=lambda: self.pen_control(True)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, text="Test Pen Down",
            command=lambda: self.pen_control(False)
        ).pack(side=tk.LEFT, padx=5)
        
        # Plotting section
        plot_frame = ttk.LabelFrame(self.plotter_frame, text="Plotting", padding=10)
        plot_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pen profile selection
        ttk.Label(plot_frame, text="Pen Profile:").pack(side=tk.LEFT, padx=5)
        self.pen_profile_var = tk.StringVar(value='ballpoint')
        if self.config:
            profiles = list(self.config.get('servo', {}).get('profiles', {}).keys())
            if profiles:
                pen_combo = ttk.Combobox(
                    plot_frame, textvariable=self.pen_profile_var,
                    values=profiles, state='readonly'
                )
                pen_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            plot_frame, text="Plot Current Image",
            command=self.plot_current_image
        ).pack(side=tk.RIGHT, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(self.plotter_frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to plot")
        self.progress_label.pack()
    
    def select_file(self):
        """Select image file."""
        filetypes = (
            ('Image files', '*.png *.jpg *.jpeg *.bmp *.tiff *.gif'),
            ('All files', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title='Select Image File',
            filetypes=filetypes
        )
        
        if filename:
            try:
                # Load and display image
                image = cv2.imread(filename)
                if image is not None:
                    self.current_image = image
                    self.display_image(image, self.image_label)
                    self.file_label.config(text=os.path.basename(filename))
                    self.status_var.set(f"Loaded: {os.path.basename(filename)}")
                else:
                    messagebox.showerror("Error", "Could not load image file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def toggle_webcam(self):
        """Toggle webcam on/off."""
        if not self.webcam_active:
            if self.webcam.start_capture():
                self.webcam_active = True
                self.webcam_button.config(text="Stop Webcam")
                self.status_var.set("Webcam active")
            else:
                error_msg = (
                    "❌ Could not start webcam\n\n"
                    "Most likely cause on macOS:\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "📷 Camera permissions not granted\n\n"
                    "How to fix:\n"
                    "1. Open System Settings\n"
                    "2. Go to Privacy & Security → Camera\n"
                    "3. Enable camera for 'Terminal' or 'Python'\n"
                    "4. Restart this application\n\n"
                    "Other possible issues:\n"
                    "• No camera connected or not working\n"
                    "• Camera in use by another app (Zoom, FaceTime, etc.)\n\n"
                    "Check the terminal/console for detailed error messages."
                )
                messagebox.showerror("Webcam Error", error_msg)
        else:
            self.webcam.stop_capture()
            self.webcam_active = False
            self.webcam_button.config(text="Start Webcam")
            self.status_var.set("Webcam stopped")
    
    def capture_webcam_image(self):
        """Capture image from webcam."""
        if self.webcam_active:
            image = self.webcam.capture_image()
            if image is not None:
                self.current_image = image
                self.display_image(image, self.image_label)
                self.status_var.set("Image captured from webcam")
            else:
                messagebox.showerror("Error", "Could not capture image")
        else:
            messagebox.showwarning("Warning", "Webcam is not active")
    
    def update_webcam(self):
        """Update webcam preview."""
        if self.webcam_active:
            frame = self.webcam.get_frame()
            if frame is not None:
                self.display_image(frame, self.image_label, max_size=(300, 200))
        
        # Schedule next update
        self.root.after(50, self.update_webcam)
    
    def display_image(self, image, label, max_size=(300, 300)):
        """Display image in label."""
        try:
            # Convert BGR to RGB
            if len(image.shape) == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Resize to fit display
            h, w = image_rgb.shape[:2]
            max_w, max_h = max_size
            
            if w > max_w or h > max_h:
                scale = min(max_w / w, max_h / h)
                new_w, new_h = int(w * scale), int(h * scale)
                image_rgb = cv2.resize(image_rgb, (new_w, new_h))
            
            # Convert to PIL and display
            image_pil = Image.fromarray(image_rgb)
            image_tk = ImageTk.PhotoImage(image_pil)
            
            label.config(image=image_tk)
            label.image = image_tk  # Keep reference
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
    
    def on_provider_changed(self, event=None):
        """Handle AI provider selection change."""
        provider_name = self.ai_provider_var.get()
        if provider_name == "None (Canny)":
            self.status_var.set("Using Canny edge detection (no AI)")
        else:
            self.status_var.set(f"Selected: {provider_name}")
    
    def configure_api_keys(self):
        """Show dialog to configure all API keys."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure AI API Keys")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Info label
        info_frame = ttk.Frame(dialog, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(
            info_frame,
            text="Configure API keys for AI caricature generation. At least one key is required to use AI mode.",
            wraplength=560
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Anthropic section
        anthro_frame = ttk.LabelFrame(dialog, text="Anthropic Claude", padding=10)
        anthro_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(anthro_frame, text="API Key:").pack(anchor=tk.W)
        anthropic_var = tk.StringVar(value=self.anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY') or "")
        anthropic_entry = ttk.Entry(anthro_frame, textvariable=anthropic_var, show="*", width=60)
        anthropic_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(anthro_frame, text="Get key: https://console.anthropic.com/", foreground="blue").pack(anchor=tk.W)
        
        show_anthro_var = tk.BooleanVar()
        ttk.Checkbutton(anthro_frame, text="Show", variable=show_anthro_var,
                       command=lambda: anthropic_entry.config(show="" if show_anthro_var.get() else "*")).pack(anchor=tk.W)
        
        # OpenAI section
        openai_frame = ttk.LabelFrame(dialog, text="OpenAI GPT-4 Vision", padding=10)
        openai_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(openai_frame, text="API Key:").pack(anchor=tk.W)
        openai_var = tk.StringVar(value=self.openai_api_key or os.environ.get('OPENAI_API_KEY') or "")
        openai_entry = ttk.Entry(openai_frame, textvariable=openai_var, show="*", width=60)
        openai_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(openai_frame, text="Get key: https://platform.openai.com/api-keys", foreground="blue").pack(anchor=tk.W)
        
        show_openai_var = tk.BooleanVar()
        ttk.Checkbutton(openai_frame, text="Show", variable=show_openai_var,
                       command=lambda: openai_entry.config(show="" if show_openai_var.get() else "*")).pack(anchor=tk.W)
        
        # Gemini section
        gemini_frame = ttk.LabelFrame(dialog, text="Google Gemini", padding=10)
        gemini_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(gemini_frame, text="API Key:").pack(anchor=tk.W)
        gemini_var = tk.StringVar(value=self.gemini_api_key or os.environ.get('GOOGLE_API_KEY') or "")
        gemini_entry = ttk.Entry(gemini_frame, textvariable=gemini_var, show="*", width=60)
        gemini_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(gemini_frame, text="Get key: https://makersuite.google.com/app/apikey", foreground="blue").pack(anchor=tk.W)
        
        show_gemini_var = tk.BooleanVar()
        ttk.Checkbutton(gemini_frame, text="Show", variable=show_gemini_var,
                       command=lambda: gemini_entry.config(show="" if show_gemini_var.get() else "*")).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X)
        
        def save_keys():
            self.anthropic_api_key = anthropic_var.get().strip() or None
            self.openai_api_key = openai_var.get().strip() or None
            self.gemini_api_key = gemini_var.get().strip() or None
            
            # Reset generator to use new keys
            self.ai_generator = None
            
            count = sum([bool(self.anthropic_api_key), bool(self.openai_api_key), bool(self.gemini_api_key)])
            if count > 0:
                messagebox.showinfo("Success", f"Saved {count} API key(s)! You can now use AI caricature mode.", parent=dialog)
            else:
                messagebox.showinfo("Info", "No API keys configured. Will use Canny edge detection.", parent=dialog)
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
    
    def init_ai_generator(self, provider: AIProvider) -> bool:
        """Initialize AI generator with specified provider."""
        try:
            self.ai_generator = AICaricatureGenerator(
                provider=provider,
                anthropic_key=self.anthropic_api_key,
                openai_key=self.openai_api_key,
                gemini_key=self.gemini_api_key
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize AI generator: {e}")
            return False
    
    def process_current_image(self):
        """Process current image with selected AI provider or Canny fallback."""
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image to process")
            return
        
        try:
            provider_name = self.ai_provider_var.get()
            
            # Map UI selection to provider
            provider_map = {
                "None (Canny)": AIProvider.NONE,
                "Anthropic Claude": AIProvider.ANTHROPIC,
                "OpenAI GPT-4V": AIProvider.OPENAI,
                "Google Gemini": AIProvider.GEMINI
            }
            
            provider = provider_map.get(provider_name, AIProvider.NONE)
            
            # Use AI if provider selected
            if provider != AIProvider.NONE:
                self.status_var.set(f"Processing with {provider_name}...")
                self.root.update()
                
                # Initialize or reinitialize generator
                if self.ai_generator is None or self.ai_generator.provider != provider:
                    if not self.init_ai_generator(provider):
                        messagebox.showerror(
                            "API Key Required",
                            f"No API key configured for {provider_name}.\n\nPlease click 'Configure API Keys' to set up."
                        )
                        return
                
                # Generate caricature
                processed, description, used_provider = self.ai_generator.generate_caricature(self.current_image)
                
                self.processed_image = processed
                self.display_image(processed, self.result_label)
                
                if used_provider == AIProvider.NONE:
                    self.status_var.set("AI unavailable - used Canny edge detection")
                else:
                    self.status_var.set(f"Processed with {used_provider.value}")
                    logger.info(f"AI: {description[:100]}...")
            
            else:
                # Use Canny edge detection
                self.status_var.set("Processing with Canny edge detection...")
                self.root.update()
                
                # Initialize generator for Canny fallback
                if self.ai_generator is None:
                    self.ai_generator = AICaricatureGenerator(provider=AIProvider.NONE)
                
                processed = self.ai_generator.enhance_edges(self.current_image)
                
                self.processed_image = processed
                self.display_image(processed, self.result_label)
                self.status_var.set("Processed with Canny edge detection")
        
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {e}")
            logger.error(f"Processing error: {e}", exc_info=True)
    
    def toggle_ai_mode(self):
        """Toggle between AI and manual processing modes."""
        use_ai = self.use_ai_var.get()
        
        # Disable manual controls when AI mode is active
        state = 'disabled' if use_ai else 'normal'
        self.method_combo.config(state='disabled' if use_ai else 'readonly')
        self.threshold1_scale.config(state=state)
        self.threshold2_scale.config(state=state)
        self.blur_scale.config(state=state)
        self.invert_check.config(state=state)
        
        if use_ai:
            self.status_var.set("AI Caricature mode enabled - processing uses Claude Haiku")
        else:
            self.status_var.set("Manual edge detection mode")
    
    def configure_api_key(self):
        """Show dialog to configure Anthropic API key."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Anthropic API Key")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Info label
        info_frame = ttk.Frame(dialog, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(
            info_frame,
            text="Enter your Anthropic API key to enable AI caricature generation.",
            wraplength=460
        ).pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(
            info_frame,
            text="Get your API key at: https://console.anthropic.com/",
            foreground="blue",
            cursor="hand2",
            wraplength=460
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Current status
        status_frame = ttk.LabelFrame(info_frame, text="Current Status", padding=5)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Check for existing API key
        env_key = os.environ.get('ANTHROPIC_API_KEY')
        current_key = self.anthropic_api_key or env_key
        
        if current_key:
            status_text = f"✓ API Key set (starts with: {current_key[:15]}...)"
            status_color = "green"
        else:
            status_text = "✗ No API key configured"
            status_color = "red"
        
        status_label = ttk.Label(status_frame, text=status_text, foreground=status_color)
        status_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(dialog, text="API Key", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(input_frame, text="Paste your API key:").pack(anchor=tk.W, pady=(0, 5))
        
        api_key_var = tk.StringVar(value=current_key or "")
        api_key_entry = ttk.Entry(input_frame, textvariable=api_key_var, show="*", width=60)
        api_key_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Show/hide toggle
        show_var = tk.BooleanVar(value=False)
        def toggle_visibility():
            api_key_entry.config(show="" if show_var.get() else "*")
        
        ttk.Checkbutton(
            input_frame,
            text="Show API key",
            variable=show_var,
            command=toggle_visibility
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Help text
        help_text = (
            "Your API key will be stored in memory for this session only.\n"
            "For permanent storage, set the ANTHROPIC_API_KEY environment variable."
        )
        ttk.Label(
            input_frame,
            text=help_text,
            foreground="gray",
            wraplength=460,
            font=("TkDefaultFont", 9)
        ).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X)
        
        def save_key():
            key = api_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Please enter an API key", parent=dialog)
                return
            
            # Validate key format
            if not key.startswith('sk-ant-'):
                result = messagebox.askyesno(
                    "Unusual Format",
                    "API key doesn't start with 'sk-ant-'. Save anyway?",
                    parent=dialog
                )
                if not result:
                    return
            
            # Save to instance variable
            self.anthropic_api_key = key
            
            # Reset generator so it uses new key
            self.caricature_generator = None
            
            messagebox.showinfo(
                "Success",
                "API key saved! You can now use AI Caricature mode.",
                parent=dialog
            )
            dialog.destroy()
        
        def test_key():
            key = api_key_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Please enter an API key to test", parent=dialog)
                return
            
            # Temporarily set key and try to initialize
            old_key = self.anthropic_api_key
            self.anthropic_api_key = key
            self.caricature_generator = None
            
            try:
                from src.utils.caricature_generator import CaricatureGenerator
                test_gen = CaricatureGenerator(api_key=key)
                messagebox.showinfo(
                    "Success",
                    "✓ API key is valid!\n\nCaricatureGenerator initialized successfully.",
                    parent=dialog
                )
            except Exception as e:
                messagebox.showerror(
                    "Test Failed",
                    f"API key validation failed:\n\n{e}",
                    parent=dialog
                )
                self.anthropic_api_key = old_key
        
        ttk.Button(button_frame, text="Test Key", command=test_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=save_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Focus on entry
        api_key_entry.focus()
        dialog.wait_window()
    
    def generate_gcode(self):
        """Generate G-code from processed image."""
        if self.processed_image is None:
            messagebox.showwarning("Warning", "No processed image. Please process an image first.")
            return
        
        try:
            # Create temporary SVG file
            svg_filename = os.path.join(self.temp_dir, "sketch.svg")
            
            # Convert processed image to SVG
            logger.info(f"Creating SVG: {svg_filename}")
            self.image_processor.image_to_svg(self.processed_image, svg_filename, 150, 100)
            self.current_svg_path = svg_filename
            
            # Initialize converter if not already done
            if self.svg_converter is None:
                config_path = "config/settings.yaml"
                if not os.path.exists(config_path):
                    config_path = "config/settings.example.yaml"
                self.svg_converter = SVGConverter(config_path)
            
            # Convert SVG to G-code
            gcode_filename = os.path.join(self.temp_dir, "sketch.gcode")
            logger.info(f"Converting to G-code: {gcode_filename}")
            
            # Always use optimization for best results
            logger.info("Using vpype optimization for path planning")
            
            self.svg_converter.convert(
                svg_filename,
                gcode_filename,
                pen_profile="ballpoint",
                optimize=True
            )
            
            self.current_gcode_path = gcode_filename
            
            # Update status
            file_size = os.path.getsize(gcode_filename)
            with open(gcode_filename, 'r') as f:
                line_count = sum(1 for line in f)
            
            status_text = f"G-code generated: {line_count} lines, {file_size} bytes"
            self.gcode_status.config(text=status_text)
            self.status_var.set("G-code generated successfully")
            
            messagebox.showinfo("Success", f"G-code generated successfully!\n{line_count} lines")
            
        except Exception as e:
            messagebox.showerror("Error", f"G-code generation failed: {e}")
            logger.error(f"G-code generation error: {e}")
    
    def view_gcode(self):
        """View generated G-code in a new window."""
        if self.current_gcode_path is None or not os.path.exists(self.current_gcode_path):
            messagebox.showwarning("Warning", "No G-code to view. Generate G-code first.")
            return
        
        try:
            # Read G-code file
            with open(self.current_gcode_path, 'r') as f:
                gcode_content = f.read()
            
            # Create viewer window
            viewer = tk.Toplevel(self.root)
            viewer.title("G-code Viewer")
            viewer.geometry("600x500")
            
            # Add title and info
            info_frame = ttk.Frame(viewer, padding=10)
            info_frame.pack(fill=tk.X)
            
            line_count = gcode_content.count('\n')
            ttk.Label(info_frame, text=f"File: {os.path.basename(self.current_gcode_path)}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Lines: {line_count}").pack(anchor=tk.W)
            
            # Add text widget with scrollbar
            text_frame = ttk.Frame(viewer)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget = tk.Text(text_frame, wrap=tk.NONE, yscrollcommand=scrollbar.set, font=("Courier", 10))
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # Insert G-code content
            text_widget.insert('1.0', gcode_content)
            text_widget.config(state=tk.DISABLED)  # Make read-only
            
            # Add close button
            ttk.Button(viewer, text="Close", command=viewer.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view G-code: {e}")
            logger.error(f"G-code viewer error: {e}")
    
    def save_gcode(self):
        """Save G-code to user-selected file."""
        if self.current_gcode_path is None or not os.path.exists(self.current_gcode_path):
            messagebox.showwarning("Warning", "No G-code to save. Generate G-code first.")
            return
        
        try:
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                title="Save G-code File",
                defaultextension=".gcode",
                filetypes=(
                    ('G-code files', '*.gcode'),
                    ('All files', '*.*')
                ),
                initialfile="sketch.gcode"
            )
            
            if filename:
                # Copy temp G-code to selected location
                import shutil
                shutil.copy2(self.current_gcode_path, filename)
                
                messagebox.showinfo("Success", f"G-code saved to:\n{filename}")
                self.status_var.set(f"G-code saved: {os.path.basename(filename)}")
                logger.info(f"G-code saved to: {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save G-code: {e}")
            logger.error(f"G-code save error: {e}")
    
    def connect_plotter(self):
        """Connect to plotter."""
        try:
            if self.plotter is None:
                config_path = "config/settings.yaml"
                if not os.path.exists(config_path):
                    config_path = "config/settings.example.yaml"
                
                self.plotter = AX5Plotter(config_path)
                self.svg_converter = SVGConverter(config_path)
            
            # Run connection in thread to avoid blocking GUI
            def connect_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(self.plotter.connect())
                    if success:
                        self.root.after(0, lambda: self.on_plotter_connected(True))
                    else:
                        self.root.after(0, lambda: self.on_plotter_connected(False))
                finally:
                    loop.close()
            
            threading.Thread(target=connect_thread, daemon=True).start()
            self.status_var.set("Connecting to plotter...")
            
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")
    
    def on_plotter_connected(self, success):
        """Called when plotter connection completes."""
        if success:
            self.plotter_status.config(text="Connected")
            self.connect_button.config(text="Disconnect", command=self.disconnect_plotter)
            self.status_var.set("Plotter connected successfully")
        else:
            self.plotter_status.config(text="Connection Failed")
            self.status_var.set("Plotter connection failed")
            messagebox.showerror("Error", "Could not connect to plotter")
    
    def disconnect_plotter(self):
        """Disconnect from plotter."""
        if self.plotter:
            def disconnect_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.plotter.disconnect())
                    self.root.after(0, self.on_plotter_disconnected)
                finally:
                    loop.close()
            
            threading.Thread(target=disconnect_thread, daemon=True).start()
    
    def on_plotter_disconnected(self):
        """Called when plotter disconnection completes."""
        self.plotter_status.config(text="Disconnected")
        self.connect_button.config(text="Connect Plotter", command=self.connect_plotter)
        self.status_var.set("Plotter disconnected")
    
    def home_plotter(self):
        """Home the plotter."""
        if not self.plotter:
            messagebox.showwarning("Warning", "Plotter not connected")
            return
        
        def home_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.root.after(0, lambda: self.status_var.set("Homing plotter..."))
                success = loop.run_until_complete(self.plotter.home())
                if success:
                    self.root.after(0, lambda: self.status_var.set("Homing completed"))
                else:
                    self.root.after(0, lambda: self.status_var.set("Homing failed"))
            finally:
                loop.close()
        
        threading.Thread(target=home_thread, daemon=True).start()
    
    def pen_control(self, down: bool):
        """Control pen up/down."""
        if not self.plotter:
            messagebox.showwarning("Warning", "Plotter not connected")
            return
        
        def pen_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.plotter.pen_control(down))
                action = "down" if down else "up"
                self.root.after(0, lambda: self.status_var.set(f"Pen {action}"))
            finally:
                loop.close()
        
        threading.Thread(target=pen_thread, daemon=True).start()
    
    def plot_current_image(self):
        """Plot the current processed image."""
        if self.processed_image is None:
            messagebox.showwarning("Warning", "No processed image to plot")
            return
        
        if not self.plotter:
            messagebox.showwarning("Warning", "Plotter not connected")
            return
        
        try:
            # Convert processed image to SVG
            svg_path = os.path.join(self.temp_dir, "sketch.svg")
            self.image_processor.image_to_svg(
                self.processed_image, svg_path,
                width_mm=140, height_mm=100  # Safe plotting area
            )
            
            # Convert SVG to G-code
            gcode_path = os.path.join(self.temp_dir, "sketch.gcode")
            self.svg_converter.convert(
                svg_path, gcode_path, 
                pen_profile=self.pen_profile_var.get()
            )
            
            # Start plotting in separate thread
            def plot_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    def progress_callback(current, total):
                        progress = (current / total) * 100 if total > 0 else 0
                        self.root.after(0, lambda: self.progress_var.set(progress))
                        self.root.after(0, lambda: self.progress_label.config(
                            text=f"Plotting: {current}/{total} lines"
                        ))
                    
                    self.root.after(0, lambda: self.status_var.set("Starting plot..."))
                    success = loop.run_until_complete(
                        self.plotter.stream_gcode(gcode_path, progress_callback)
                    )
                    
                    if success:
                        self.root.after(0, lambda: self.status_var.set("Plot completed"))
                        self.root.after(0, lambda: self.progress_var.set(100))
                        self.root.after(0, lambda: self.progress_label.config(text="Plot completed"))
                    else:
                        self.root.after(0, lambda: self.status_var.set("Plot failed"))
                        
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Plot failed: {e}"))
                    self.root.after(0, lambda: self.status_var.set("Plot error"))
                finally:
                    loop.close()
            
            threading.Thread(target=plot_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare plot: {e}")
    
    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        finally:
            # Cleanup
            if self.webcam_active:
                self.webcam.stop_capture()
            if self.plotter:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.plotter.disconnect())
                    loop.close()
                except:
                    pass


def main():
    """Main entry point."""
    print("AX5 Plotter Simple Local Application")
    print("====================================")
    
    # Check for required directories
    if not os.path.exists("config"):
        print("Error: config directory not found")
        print("Please run this from the project root directory")
        return 1
    
    # Check for configuration
    if not os.path.exists("config/settings.yaml") and not os.path.exists("config/settings.example.yaml"):
        print("Error: No configuration file found")
        print("Please ensure config/settings.yaml or config/settings.example.yaml exists")
        return 1
    
    # Create application and run
    try:
        app = SimplePlotterApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 1
    except Exception as e:
        print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())