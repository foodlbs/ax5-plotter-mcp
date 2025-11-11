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
            image: Processed image array
            output_path: Path to save SVG
            width_mm: Target width in mm
            height_mm: Target height in mm
            
        Returns:
            str: Path to created SVG file
        """
        # Find contours in the image
        contours, _ = cv2.findContours(
            image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
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
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                return False
            
            # Set resolution for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.is_capturing = True
            return True
        except Exception as e:
            logger.error(f"Failed to start webcam: {e}")
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
        
        # Current image and processing state
        self.current_image = None
        self.processed_image = None
        self.temp_dir = tempfile.mkdtemp()
        
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
        """Setup image processing tab."""
        # Processing controls
        controls_frame = ttk.LabelFrame(self.process_frame, text="Processing Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Method selection
        ttk.Label(controls_frame, text="Method:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.method_var = tk.StringVar(value='canny')
        method_combo = ttk.Combobox(
            controls_frame, textvariable=self.method_var,
            values=list(self.image_processor.methods.values()),
            state='readonly'
        )
        method_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Threshold controls
        ttk.Label(controls_frame, text="Threshold 1:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.threshold1_var = tk.IntVar(value=50)
        ttk.Scale(
            controls_frame, from_=1, to=255, orient=tk.HORIZONTAL,
            variable=self.threshold1_var, length=200
        ).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(controls_frame, text="Threshold 2:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.threshold2_var = tk.IntVar(value=150)
        ttk.Scale(
            controls_frame, from_=1, to=255, orient=tk.HORIZONTAL,
            variable=self.threshold2_var, length=200
        ).grid(row=2, column=1, padx=5, pady=2)
        
        # Blur control
        ttk.Label(controls_frame, text="Blur:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.blur_var = tk.IntVar(value=1)
        ttk.Scale(
            controls_frame, from_=1, to=15, orient=tk.HORIZONTAL,
            variable=self.blur_var, length=200
        ).grid(row=3, column=1, padx=5, pady=2)
        
        # Invert option
        self.invert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls_frame, text="Invert (white background)",
            variable=self.invert_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Process button
        ttk.Button(
            controls_frame, text="Process Image",
            command=self.process_current_image
        ).grid(row=5, column=0, columnspan=2, pady=10)
        
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
            command=lambda: self.pen_control(False)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, text="Test Pen Down",
            command=lambda: self.pen_control(True)
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
                messagebox.showerror("Error", "Could not start webcam")
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
        if self.webcam_active and not self.current_image is None:
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
    
    def process_current_image(self):
        """Process current image to sketch."""
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image to process")
            return
        
        try:
            # Get method key from display name
            method_name = self.method_var.get()
            method_key = None
            for key, name in self.image_processor.methods.items():
                if name == method_name:
                    method_key = key
                    break
            
            if method_key is None:
                method_key = 'canny'
            
            # Process image
            processed = self.image_processor.process_image(
                self.current_image,
                method=method_key,
                threshold1=self.threshold1_var.get(),
                threshold2=self.threshold2_var.get(),
                blur=self.blur_var.get(),
                invert=self.invert_var.get()
            )
            
            self.processed_image = processed
            self.display_image(processed, self.result_label)
            self.status_var.set("Image processed successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {e}")
            logger.error(f"Image processing error: {e}")
    
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