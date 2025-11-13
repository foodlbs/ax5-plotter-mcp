#!/usr/bin/env python3
"""
AX5 Plotter Photo Booth Application

Enhanced photo booth with live preview, style options, queue management,
and email delivery.

Features:
- Live camera preview
- Multiple image styles (cartoon, sketch, comic, etc.)
- User information capture (name & email)
- Print queue with dashboard
- Email delivery of processed images
- Queue persistence

Usage:
    python photo_booth_app.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import os
import sys
import threading
import logging
from PIL import Image, ImageTk
from typing import Optional
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.plotter.ax5 import AX5Plotter
from src.utils.svg_converter import SVGConverter
from src.utils.ai_caricature_generator import AICaricatureGenerator, AIProvider
from src.utils.print_queue import PrintQueue, PrintJob, JobStatus, ImageStyle

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Style prompt templates for AI
STYLE_PROMPTS = {
    ImageStyle.CARTOON: "Create a simple cartoon-style line drawing with bold outlines, minimal shading, and playful exaggerated features. Focus on clean, smooth curves suitable for pen plotting.",
    ImageStyle.SKETCH: "Create a hand-drawn sketch with loose, artistic lines. Include some hatching for shading but keep it sparse and organic. Focus on capturing the essence rather than details.",
    ImageStyle.COMIC: "Create a comic book style illustration with strong black outlines, dramatic angles, and bold line work. Emphasize contrast and dynamic composition.",
    ImageStyle.OUTLINE: "Create a minimal line drawing with only the most essential outlines. No shading, no details - just pure contours capturing the basic shape and features.",
    ImageStyle.ARTISTIC: "Create an artistic interpretation with varied line weights, flowing curves, and creative expression. Balance detail with negative space for visual interest.",
    ImageStyle.MINIMAL: "Create an extremely minimal line drawing using as few lines as possible. Focus only on the most distinctive features with elegant simplicity."
}


# Color scheme - Standard UI colors (lower contrast)
BG_COLOR = "#f0f0f0"  # Light gray background
CARD_BG = "#ffffff"  # White cards
CARD_BORDER = "#d0d0d0"  # Light border
TEXT_COLOR = "#2c3e50"  # Dark blue-gray text
TEXT_SECONDARY = "#7f8c8d"  # Gray secondary text
ACCENT_COLOR = "#3498db"  # Blue accent
BUTTON_HOVER = "#2980b9"  # Darker blue on hover

class PhotoBoothApp:
    """Photo booth application with queue management."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AX5 Plotter Photo Booth")
        self.root.geometry("1600x950")
        
        # Apply modern startup styling
        self.root.configure(bg=BG_COLOR)
        
        # Configure ttk styles with modern look
        style = ttk.Style()
        style.theme_use('default')
        
        # Frame styles - clean cards
        style.configure('TFrame', background=BG_COLOR)
        style.configure('Card.TFrame', background=CARD_BG)
        
        # LabelFrame with modern styling
        style.configure('TLabelframe', 
                       background=CARD_BG, 
                       foreground=TEXT_COLOR,
                       borderwidth=1,
                       relief='solid')
        style.configure('TLabelframe.Label', 
                       background=CARD_BG, 
                       foreground=ACCENT_COLOR, 
                       font=('SF Pro Display', 12, 'bold'))
        
        # Modern button styles
        style.configure('Accent.TButton', 
                       background=ACCENT_COLOR,
                       foreground='white',
                       borderwidth=0,
                       font=('SF Pro Display', 11, 'bold'),
                       padding=(20, 12))
        style.map('Accent.TButton',
                 background=[('active', BUTTON_HOVER), ('disabled', '#555555')],
                 foreground=[('disabled', '#888888')])
        
        # Label styles
        style.configure('TLabel', 
                       background=CARD_BG, 
                       foreground=TEXT_COLOR, 
                       font=('SF Pro Text', 11))
        style.configure('Title.TLabel',
                       background=BG_COLOR,
                       foreground=TEXT_COLOR,
                       font=('SF Pro Display', 24, 'bold'))
        
        # Entry styles
        style.configure('Modern.TEntry',
                       fieldbackground='white',
                       foreground='black',
                       borderwidth=1,
                       relief='solid')
        
        # Radiobutton with modern look
        style.configure('Modern.TRadiobutton',
                       background=CARD_BG,
                       foreground=TEXT_COLOR,
                       font=('SF Pro Text', 10),
                       indicatorcolor=ACCENT_COLOR)
        style.map('Modern.TRadiobutton',
                 background=[('active', CARD_BG)],
                 foreground=[('selected', ACCENT_COLOR)])
        
        # Notebook (tabs) styling
        style.configure('TNotebook', 
                       background=BG_COLOR,
                       borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=CARD_BG,
                       foreground=TEXT_SECONDARY,
                       padding=[20, 10],
                       borderwidth=0,
                       font=('SF Pro Text', 11))
        style.map('TNotebook.Tab',
                 background=[('selected', BG_COLOR)],
                 foreground=[('selected', ACCENT_COLOR)])
        
        # Configuration
        self.config = self.load_config()
        
        # Camera
        self.camera = None
        self.camera_running = False
        self.captured_frame = None
        self.processed_frame = None  # Store processed image
        self.processed_image_path = None  # Store path to processed image
        
        # Queue system
        self.print_queue = PrintQueue()
        self.queue_file = "queue_state.json"
        self.print_queue.load_from_file(self.queue_file)
        self.print_queue.add_observer(self.update_queue_display)
        self.processing_thread = None
        self.processing_active = False
        
        # Output directory for saved images
        self.output_base_dir = Path("output/saved_images")
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        # AI providers - load from config first, can be overridden via UI
        ai_config = self.config.get('ai', {})
        api_keys = ai_config.get('api_keys', {})
        
        self.anthropic_api_key = api_keys.get('anthropic') or None
        self.openai_api_key = api_keys.get('openai') or None
        self.gemini_api_key = api_keys.get('gemini') or None
        
        # Load model names from config
        models = ai_config.get('models', {})
        self.anthropic_model = models.get('anthropic', 'claude-3-5-sonnet-20241022')
        self.openai_model = models.get('openai', 'gpt-4o')
        self.gemini_model = models.get('gemini', 'gemini-2.5-flash')
        
        self.ai_generator = None
        
        # Plotter connection
        self.plotter = None
        self.plotter_connected = False
        
        # UI
        self.setup_ui()
        
        # Start camera
        self.start_camera()
        
        # Start processing thread
        self.start_processing_thread()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self) -> dict:
        """Load configuration."""
        try:
            with open("config/settings.yaml", 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def on_streaming_progress(self, current: int, total: int):
        """Callback for G-code streaming progress."""
        percentage = int((current / total) * 100) if total > 0 else 0
        status_text = f"Streaming line {current} of {total} ({percentage}%)"
        self.update_streaming_progress(current, total, status_text)
    
    def update_streaming_progress(self, current: int, total: int, status: str):
        """Update streaming progress display (thread-safe)."""
        try:
            percentage = int((current / total) * 100) if total > 0 else 0
            
            # Update UI from main thread
            self.root.after(0, lambda: self.streaming_progress.config(value=percentage))
            self.root.after(0, lambda: self.streaming_label.config(text=status))
            
            # If complete, reset after 3 seconds
            if percentage >= 100:
                self.root.after(3000, self.clear_streaming_progress)
        except Exception as e:
            logger.error(f"Error updating streaming progress: {e}")
    
    def clear_streaming_progress(self):
        """Clear streaming progress display."""
        try:
            self.streaming_progress.config(value=0)
            self.streaming_label.config(text="No active streaming")
        except Exception as e:
            logger.error(f"Error clearing streaming progress: {e}")
    
    def setup_ui(self):
        """Create UI layout."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab 1: Photo Booth
        photo_booth_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(photo_booth_tab, text="📸 Photo Booth")
        
        # Tab 2: Queue Management
        queue_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(queue_tab, text="🖨️ Queue Management")
        
        # Setup Photo Booth tab content
        self.setup_photo_booth_tab(photo_booth_tab)
        
        # Setup Queue Management tab content
        self.setup_queue_tab(queue_tab)
    
    def setup_photo_booth_tab(self, parent):
        """Setup the photo booth tab."""
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # Left panel - Camera and capture
        left_panel = ttk.Frame(parent, padding="5")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Live preview
        preview_frame = ttk.LabelFrame(left_panel, text="Live Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.live_label = tk.Label(preview_frame, bg='black', borderwidth=0)
        self.live_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Captured image
        capture_frame = ttk.LabelFrame(left_panel, text="Captured Photo", padding="10")
        capture_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.capture_label = tk.Label(capture_frame, bg=CARD_BG, fg=TEXT_SECONDARY, 
                                      text="No photo captured", 
                                      font=('SF Pro Text', 11),
                                      borderwidth=0)
        self.capture_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Capture controls
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            controls_frame,
            text="📸 Capture Photo",
            command=self.capture_photo,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        ttk.Button(
            controls_frame,
            text="🔄 Retake",
            command=self.clear_capture,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # Center panel - User info and style
        center_panel = ttk.Frame(parent, padding="5")
        center_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        
        # User information
        info_frame = ttk.LabelFrame(center_panel, text="Your Information", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(info_frame, text="Name:", font=('SF Pro Text', 11)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.name_entry = ttk.Entry(info_frame, width=35, font=('SF Pro Text', 12), style='Modern.TEntry')
        self.name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=8, padx=(15, 0))
        
        ttk.Label(info_frame, text="Email:", font=('SF Pro Text', 11)).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.email_entry = ttk.Entry(info_frame, width=35, font=('SF Pro Text', 12), style='Modern.TEntry')
        self.email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=8, padx=(15, 0))
        
        info_frame.columnconfigure(1, weight=1)
        
        # Style selection
        style_frame = ttk.LabelFrame(center_panel, text="Choose Your Style", padding="15")
        style_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.style_var = tk.StringVar(value=ImageStyle.CARTOON.value)
        
        styles = [
            ("🎨 Cartoon", ImageStyle.CARTOON.value, "Bold, playful outlines"),
            ("✏️ Sketch", ImageStyle.SKETCH.value, "Artistic hand-drawn look"),
            ("💥 Comic", ImageStyle.COMIC.value, "Dynamic comic book style"),
            ("〰️ Outline", ImageStyle.OUTLINE.value, "Pure minimal outlines"),
            ("🖼️ Artistic", ImageStyle.ARTISTIC.value, "Expressive line art"),
            ("⚪ Minimal", ImageStyle.MINIMAL.value, "Ultra-simple lines")
        ]
        
        for i, (label, value, desc) in enumerate(styles):
            row = i // 2
            col = i % 2
            
            frame = ttk.Frame(style_frame)
            frame.grid(row=row, column=col, sticky=(tk.W, tk.E), padx=10, pady=8)
            
            radio = ttk.Radiobutton(
                frame,
                text=label,
                variable=self.style_var,
                value=value,
                style='Modern.TRadiobutton'
            )
            radio.pack(anchor=tk.W)
            
            desc_label = ttk.Label(frame, text=desc, foreground='gray', font=('Arial', 9))
            desc_label.pack(anchor=tk.W, padx=(20, 0))
        
        style_frame.columnconfigure(0, weight=1)
        style_frame.columnconfigure(1, weight=1)
        
        # AI Provider
        ai_frame = ttk.LabelFrame(center_panel, text="AI Provider", padding="10")
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(ai_frame, text="Provider:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.ai_provider_var = tk.StringVar(value="None (Canny)")
        self.ai_provider_combo = ttk.Combobox(
            ai_frame,
            textvariable=self.ai_provider_var,
            state='readonly',
            width=20
        )
        self.ai_provider_combo['values'] = [
            "None (Canny)",
            "Anthropic Claude",
            "OpenAI GPT-4",
            "Google Gemini"
        ]
        self.ai_provider_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            ai_frame,
            text="⚙️ Configure API Keys",
            command=self.configure_api_keys,
            style='Accent.TButton'
        ).pack(side=tk.LEFT)
        
        # Action buttons - side by side (BEFORE preview so they're always visible)
        btn_frame = ttk.Frame(center_panel)
        btn_frame.pack(fill=tk.X, pady=(15, 15))
        
        self.generate_btn = ttk.Button(
            btn_frame,
            text="🎨 Generate Preview",
            command=self.generate_preview,
            state=tk.DISABLED,
            style='Accent.TButton'
        )
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.add_queue_btn = ttk.Button(
            btn_frame,
            text="🖨️ Add to Print Queue",
            command=self.add_to_queue,
            state=tk.DISABLED,
            style='Accent.TButton'
        )
        self.add_queue_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        
        # Preview processed image (AFTER buttons)
        preview_processed_frame = ttk.LabelFrame(center_panel, text="Preview Processed Image", padding="15")
        preview_processed_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.processed_preview_label = tk.Label(
            preview_processed_frame, 
            bg=CARD_BG, 
            fg=ACCENT_COLOR,
            text="✨ Preview will appear here after clicking 'Generate Preview'",
            font=('SF Pro Display', 13),
            borderwidth=0
        )
        self.processed_preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_queue_tab(self, parent):
        """Setup the queue management tab."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # Queue dashboard
        queue_frame = ttk.LabelFrame(parent, text="Print Queue Dashboard", padding="10")
        queue_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Queue stats
        stats_frame = ttk.Frame(queue_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.queue_stats_label = ttk.Label(
            stats_frame,
            text="Queued: 0 | Processing: 0 | Completed: 0",
            font=('Arial', 10, 'bold')
        )
        self.queue_stats_label.pack()
        
        # Streaming progress frame
        progress_frame = ttk.LabelFrame(queue_frame, text="G-code Streaming Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress label
        self.streaming_label = ttk.Label(
            progress_frame,
            text="No active streaming",
            font=('Arial', 9)
        )
        self.streaming_label.pack(anchor=tk.W)
        
        # Progress bar
        self.streaming_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.streaming_progress.pack(fill=tk.X, pady=(5, 0))
        
        # Queue list
        list_frame = ttk.Frame(queue_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.queue_tree = ttk.Treeview(
            list_frame,
            columns=('Name', 'Style', 'Status', 'Retries', 'Time'),
            show='headings',
            yscrollcommand=scrollbar.set,
            height=10
        )
        self.queue_tree.heading('Name', text='Name')
        self.queue_tree.heading('Style', text='Style')
        self.queue_tree.heading('Status', text='Status')
        self.queue_tree.heading('Retries', text='Retries')
        self.queue_tree.heading('Time', text='Time')
        
        self.queue_tree.column('Name', width=120)
        self.queue_tree.column('Style', width=100)
        self.queue_tree.column('Status', width=120)
        self.queue_tree.column('Retries', width=60)
        self.queue_tree.column('Time', width=80)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.queue_tree.yview)
        
        # Queue controls
        queue_ctrl_frame = ttk.Frame(queue_frame)
        queue_ctrl_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            queue_ctrl_frame,
            text="🖨️ Connect Printer",
            command=self.connect_printer,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            queue_ctrl_frame,
            text="✅ Approve & Print",
            command=self.approve_selected_job,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            queue_ctrl_frame,
            text="🔄 Retry Failed",
            command=self.retry_selected_job,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            queue_ctrl_frame,
            text="❌ Cancel Selected",
            command=self.cancel_selected_job,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            queue_ctrl_frame,
            text="🔄 Refresh",
            command=self.update_queue_display,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        # Initial queue update
        self.update_queue_display()
    
    def start_camera(self):
        """Start camera capture."""
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            messagebox.showerror("Camera Error", "Could not open camera")
            return
        
        self.camera_running = True
        self.update_live_preview()
    
    def update_live_preview(self):
        """Update live camera preview."""
        if not self.camera_running or not self.camera:
            return
        
        ret, frame = self.camera.read()
        if ret:
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit preview
            height, width = frame_rgb.shape[:2]
            max_width = 400
            max_height = 300
            
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            # Convert to ImageTk
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.live_label.imgtk = imgtk
            self.live_label.configure(image=imgtk)
        
        # Schedule next update
        if self.camera_running:
            self.root.after(30, self.update_live_preview)
    
    def capture_photo(self):
        """Capture photo from camera."""
        if not self.camera or not self.camera.isOpened():
            messagebox.showerror("Error", "Camera not available")
            return
        
        ret, frame = self.camera.read()
        if ret:
            self.captured_frame = frame.copy()
            
            # Display captured image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize for display
            height, width = frame_rgb.shape[:2]
            max_width = 400
            max_height = 300
            
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.capture_label.imgtk = imgtk
            self.capture_label.configure(image=imgtk, text="")
            
            # Enable generate preview button
            self.generate_btn.config(state=tk.NORMAL)
            # Keep add to queue disabled until preview generated
            self.add_queue_btn.config(state=tk.DISABLED)
            
            # Clear any previous processed image
            self.processed_frame = None
            self.processed_image_path = None
            self.processed_preview_label.configure(
                image='', 
                text="Click 'Generate Preview' to see your processed image"
            )
            
            logger.info("Photo captured successfully")
        else:
            messagebox.showerror("Error", "Failed to capture photo")
    
    def clear_capture(self):
        """Clear captured photo."""
        self.captured_frame = None
        self.processed_frame = None
        self.processed_image_path = None
        self.capture_label.configure(image='', text="No photo captured")
        self.processed_preview_label.configure(
            image='', 
            text="Click 'Generate Preview' to see your processed image"
        )
        self.generate_btn.config(state=tk.DISABLED)
        self.add_queue_btn.config(state=tk.DISABLED)
    
    def generate_preview(self):
        """Generate and display preview of processed image."""
        if self.captured_frame is None:
            messagebox.showwarning("No Photo", "Please capture a photo first")
            return
        
        # Show processing message
        self.processed_preview_label.configure(text="⏳ Processing... Please wait...")
        self.root.update()
        
        try:
            # Get selected style and provider
            style = ImageStyle(self.style_var.get())
            ai_provider = self.ai_provider_var.get()
            
            # Get style prompt
            style_prompt = STYLE_PROMPTS.get(style, "")
            
            # Determine provider
            if "Anthropic" in ai_provider:
                provider = AIProvider.ANTHROPIC
            elif "OpenAI" in ai_provider:
                provider = AIProvider.OPENAI
            elif "Gemini" in ai_provider:
                provider = AIProvider.GEMINI
            else:
                provider = AIProvider.NONE
            
            logger.info(f"Generating preview with {ai_provider}, style: {style.value}")
            
            # Process based on provider
            if provider != AIProvider.NONE:
                # Initialize AI generator if needed
                if not self.ai_generator:
                    self.ai_generator = AICaricatureGenerator(
                        provider=provider,
                        anthropic_key=self.anthropic_api_key,
                        openai_key=self.openai_api_key,
                        gemini_key=self.gemini_api_key,
                        anthropic_model=self.anthropic_model,
                        openai_model=self.openai_model,
                        gemini_model=self.gemini_model
                    )
                else:
                    self.ai_generator.set_provider(provider)
                
                # Generate with AI
                processed_img, description, provider_used = self.ai_generator.generate_caricature(
                    self.captured_frame
                )
                logger.info(f"AI processed with {provider_used.value}: {description}")
            else:
                # Use Canny edge detection
                gray = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2GRAY)
                processed_img = cv2.Canny(gray, 50, 150)
                logger.info("Processed with Canny edge detection")
            
            # Store processed image
            self.processed_frame = processed_img
            
            # Save to temp file
            temp_dir = Path("output/temp_processed")
            temp_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.processed_image_path = temp_dir / f"preview_{timestamp}.png"
            cv2.imwrite(str(self.processed_image_path), processed_img)
            
            # Generate G-code immediately after processing
            from src.utils.svg_converter import SVGConverter
            converter = SVGConverter()
            
            gcode_dir = Path("output/gcode")
            gcode_dir.mkdir(parents=True, exist_ok=True)
            gcode_path = gcode_dir / f"preview_{timestamp}.gcode"
            
            logger.info(f"Generating G-code from processed image...")
            try:
                converter.convert_image_to_gcode(
                    str(self.processed_image_path),
                    str(gcode_path)
                )
                logger.info(f"G-code generated: {gcode_path}")
            except Exception as gcode_error:
                logger.warning(f"G-code generation failed: {gcode_error}")
                # Continue even if G-code fails
            
            # Display processed image
            # Convert to RGB for display
            if len(processed_img.shape) == 2:
                # Grayscale to RGB
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
            else:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            
            # Resize for display
            height, width = display_img.shape[:2]
            max_width = 700
            max_height = 500
            
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            display_resized = cv2.resize(display_img, (new_width, new_height))
            
            # Convert to ImageTk
            img = Image.fromarray(display_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.processed_preview_label.imgtk = imgtk
            self.processed_preview_label.configure(image=imgtk, text="")
            
            # Enable add to queue button
            self.add_queue_btn.config(state=tk.NORMAL)
            
            logger.info("Preview generated successfully")
            messagebox.showinfo(
                "Preview Ready",
                f"✅ Your {style.value} style preview is ready!\n\n"
                f"G-code generated and ready for plotting.\n\n"
                "If you like it, click 'Add to Print Queue'.\n"
                "To try a different style, select it and click 'Generate Preview' again."
            )
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            messagebox.showerror("Error", f"Failed to generate preview: {e}")
            self.processed_preview_label.configure(
                image='',
                text="❌ Preview generation failed. Try again."
            )
    
    def add_to_queue(self):
        """Add captured photo to print queue."""
        # Validate inputs
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Missing Information", "Please enter your name")
            return
        
        if not email or '@' not in email:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address")
            return
        
        if self.processed_frame is None:
            messagebox.showwarning("No Preview", "Please generate a preview first by clicking 'Generate Preview'")
            return
        
        try:
            # Save original captured image
            temp_dir = Path("output/captures")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = temp_dir / f"capture_{timestamp}.jpg"
            cv2.imwrite(str(image_path), self.captured_frame)
            
            # Copy processed image to processed folder (already generated in preview)
            processed_dir = Path("output/processed")
            processed_dir.mkdir(parents=True, exist_ok=True)
            processed_path = processed_dir / f"processed_{timestamp}.png"
            cv2.imwrite(str(processed_path), self.processed_frame)
            
            # Get style and provider
            style = ImageStyle(self.style_var.get())
            ai_provider = self.ai_provider_var.get()
            
            # Add to queue with already-processed image path
            job_id = self.print_queue.add_job(
                name=name,
                email=email,
                image_path=str(processed_path),  # Use processed image, not original
                style=style,
                ai_provider=ai_provider
            )
            
            # Set status to pending approval (requires manual approval before printing)
            job = self.print_queue.get_job(job_id)
            if job:
                job.status = JobStatus.PENDING_APPROVAL
            
            # Save queue state
            self.print_queue.save_to_file(self.queue_file)
            
            # Show confirmation
            position = self.print_queue.get_queue_position(job_id)
            messagebox.showinfo(
                "Added to Queue",
                f"Thank you {name}!\n\n"
                f"Your {style.value} portrait has been added to the queue.\n"
                f"⚠️ Requires manual approval before printing.\n"
                f"Queue position: {position}\n\n"
                f"Go to Queue Management tab to approve and print."
            )
            
            # Clear form
            self.name_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.clear_capture()
            
            logger.info(f"Job {job_id} added to queue for {name}")
            
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            messagebox.showerror("Error", f"Failed to add to queue: {e}")
    
    def start_processing_thread(self):
        """Start background thread for processing queue."""
        self.processing_active = True
        self.processing_thread = threading.Thread(
            target=self.process_queue_worker,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Processing thread started")
    
    def process_queue_worker(self):
        """Worker thread that processes queue jobs."""
        while self.processing_active:
            try:
                # Get next job (only approved jobs)
                job_id = self.print_queue.get_next_job()
                
                if job_id:
                    job = self.print_queue.get_job(job_id)
                    # Only process if approved
                    if job and job.approved_for_print:
                        self.process_job(job)
                    elif job and not job.approved_for_print:
                        logger.info(f"Job {job_id} waiting for approval")
                    
                    # Save queue state after processing
                    self.print_queue.save_to_file(self.queue_file)
                else:
                    # No jobs, wait a bit
                    threading.Event().wait(2)
                    
            except Exception as e:
                logger.error(f"Error in processing thread: {e}")
                threading.Event().wait(5)
    
    def process_job(self, job: PrintJob):
        """Process a single print job."""
        logger.info(f"Processing job {job.job_id} for {job.name}")
        
        try:
            # Update status
            self.print_queue.update_status(job.job_id, JobStatus.PROCESSING)
            
            # Load already-processed image (processing was done in preview)
            processed_img = cv2.imread(job.image_path)
            if processed_img is None:
                raise Exception("Failed to load processed image")
            
            logger.info(f"Using pre-processed image from preview: {job.image_path}")
            
            # Save processed image to organized folder
            # Create user-specific folder: output/saved_images/Name_Email/
            safe_name = job.name.replace(' ', '_').replace('/', '_')
            safe_email = job.email.replace('@', '_at_').replace('.', '_')
            user_folder = self.output_base_dir / f"{safe_name}_{safe_email}"
            user_folder.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save processed image in user folder
            processed_filename = f"{job.style.value}_{timestamp}.png"
            user_processed_path = user_folder / processed_filename
            cv2.imwrite(str(user_processed_path), processed_img)
            
            self.print_queue.update_paths(
                job.job_id,
                processed_image_path=str(user_processed_path)
            )
            
            logger.info(f"Processed image saved to: {user_processed_path}")
            
            # Convert to G-code
            self.print_queue.update_status(job.job_id, JobStatus.PLOTTING)
            
            gcode_filename = f"{job.style.value}_{timestamp}.gcode"
            user_gcode_path = user_folder / gcode_filename
            
            converter = SVGConverter(self.config)
            success, svg_path = converter.image_to_svg(
                str(user_processed_path),  # Use the processed image we just saved
                str(user_gcode_path)
            )
            
            if not success:
                raise Exception("G-code conversion failed")
            
            self.print_queue.update_paths(
                job.job_id,
                gcode_path=str(user_gcode_path)
            )
            
            logger.info(f"G-code generated: {user_gcode_path}")
            logger.info(f"All files saved to: {user_folder}")
            
            # Stream to plotter with progress tracking
            if self.plotter and self.plotter_connected:
                # Read G-code file
                with open(user_gcode_path, 'r') as f:
                    gcode_content = f.read()
                
                # Update UI to show streaming started
                self.update_streaming_progress(0, 100, "Starting G-code streaming...")
                
                # Stream with progress callback
                import asyncio
                success = asyncio.run(
                    self.plotter.stream_gcode(
                        str(user_gcode_path),
                        progress_callback=self.on_streaming_progress
                    )
                )
                
                if not success:
                    raise Exception("G-code streaming failed")
                
                # Clear progress display
                self.update_streaming_progress(100, 100, "Streaming complete!")
            else:
                logger.info("Plotter not connected - skipping streaming")
            
            # Mark complete
            self.print_queue.update_status(job.job_id, JobStatus.COMPLETED)
            logger.info(f"Job {job.job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {e}")
            self.print_queue.update_status(
                job.job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
    
    def update_queue_display(self):
        """Update queue dashboard display."""
        try:
            # Update stats
            stats = self.print_queue.get_statistics()
            pending = sum(1 for job in self.print_queue.get_all_jobs() if job.status == JobStatus.PENDING_APPROVAL)
            self.queue_stats_label.config(
                text=f"Pending: {pending} | Queued: {stats['queued']} | "
                     f"Processing: {stats['processing'] + stats['plotting']} | "
                     f"Completed: {stats['completed']}"
            )
            
            # Update tree
            self.queue_tree.delete(*self.queue_tree.get_children())
            
            jobs = self.print_queue.get_all_jobs()
            for job in jobs:
                # Format time
                created = datetime.fromtimestamp(job.created_at)
                time_str = created.strftime("%H:%M")
                
                # Status with emoji
                status_icons = {
                    JobStatus.PENDING_APPROVAL: "⏸️",
                    JobStatus.QUEUED: "⏳",
                    JobStatus.PROCESSING: "⚙️",
                    JobStatus.PLOTTING: "🖨️",
                    JobStatus.COMPLETED: "✅",
                    JobStatus.FAILED: "❌",
                    JobStatus.CANCELLED: "🚫"
                }
                status_text = f"{status_icons.get(job.status, '')} {job.status.value}"
                
                self.queue_tree.insert(
                    '',
                    0,  # Insert at top
                    values=(
                        job.name,
                        job.style.value.capitalize(),
                        status_text,
                        job.retry_count,
                        time_str
                    ),
                    tags=(job.job_id,)
                )
        
        except Exception as e:
            logger.error(f"Error updating queue display: {e}")
    
    def cancel_selected_job(self):
        """Cancel selected job in queue."""
        selection = self.queue_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to cancel")
            return
        
        item = selection[0]
        tags = self.queue_tree.item(item, 'tags')
        
        if tags:
            job_id = tags[0]
            job = self.print_queue.get_job(job_id)
            
            if job and job.status == JobStatus.QUEUED:
                self.print_queue.cancel_job(job_id)
                self.print_queue.save_to_file(self.queue_file)
                messagebox.showinfo("Cancelled", f"Job for {job.name} has been cancelled")
            else:
                messagebox.showwarning("Cannot Cancel", "Only queued jobs can be cancelled")
    
    def approve_selected_job(self):
        """Approve selected job for printing."""
        selection = self.queue_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to approve")
            return
        
        item = selection[0]
        tags = self.queue_tree.item(item, 'tags')
        
        if tags:
            job_id = tags[0]
            job = self.print_queue.get_job(job_id)
            
            if job and job.status == JobStatus.PENDING_APPROVAL:
                job.approved_for_print = True
                job.status = JobStatus.QUEUED
                self.print_queue.save_to_file(self.queue_file)
                messagebox.showinfo("Approved", f"Job for {job.name} has been approved for printing!")
                logger.info(f"Job {job_id} approved for printing")
            else:
                messagebox.showwarning("Cannot Approve", "Only pending jobs can be approved")
    
    def retry_selected_job(self):
        """Retry a failed job."""
        selection = self.queue_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a failed job to retry")
            return
        
        item = selection[0]
        tags = self.queue_tree.item(item, 'tags')
        
        if tags:
            job_id = tags[0]
            job = self.print_queue.get_job(job_id)
            
            if job and job.status == JobStatus.FAILED:
                job.status = JobStatus.PENDING_APPROVAL
                job.retry_count += 1
                job.error_message = None
                job.approved_for_print = False
                self.print_queue.save_to_file(self.queue_file)
                messagebox.showinfo("Retry", f"Job for {job.name} moved back to queue (Retry #{job.retry_count})")
                logger.info(f"Job {job_id} retry #{job.retry_count}")
            else:
                messagebox.showwarning("Cannot Retry", "Only failed jobs can be retried")
    
    def connect_printer(self):
        """Connect to the AX5 plotter."""
        try:
            # Import plotter classes
            from src.plotter.grbl import GRBLController
            
            # Create connection dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Connect to Plotter")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.configure(bg=BG_COLOR)
            
            # Content frame
            content = ttk.Frame(dialog, padding="20")
            content.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(content, text="Serial Port:", font=('SF Pro Text', 11)).pack(anchor=tk.W, pady=(0, 5))
            
            port_var = tk.StringVar(value="/dev/cu.usbserial-0001")
            port_entry = ttk.Entry(content, textvariable=port_var, width=40)
            port_entry.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(content, text="Baud Rate:", font=('SF Pro Text', 11)).pack(anchor=tk.W, pady=(0, 5))
            
            baud_var = tk.StringVar(value="115200")
            baud_entry = ttk.Entry(content, textvariable=baud_var, width=40)
            baud_entry.pack(fill=tk.X, pady=(0, 20))
            
            def do_connect():
                try:
                    # Create plotter instance
                    port = port_var.get().strip()
                    baud = int(baud_var.get().strip())
                    
                    self.plotter = GRBLController(
                        port=port,
                        baud_rate=baud
                    )
                    
                    # Connect asynchronously
                    import asyncio
                    success = asyncio.run(self.plotter.connect())
                    
                    if success:
                        self.plotter_connected = True
                        messagebox.showinfo("Success", f"Connected to plotter on {port}")
                        dialog.destroy()
                        logger.info(f"Plotter connected: {port} @ {baud}")
                    else:
                        raise Exception("Connection failed")
                        
                except Exception as e:
                    messagebox.showerror("Connection Error", f"Failed to connect:\n{e}")
                    logger.error(f"Plotter connection error: {e}")
            
            # Connect button
            ttk.Button(
                content,
                text="Connect",
                command=do_connect,
                style='Accent.TButton'
            ).pack(fill=tk.X)
            
        except Exception as e:
            logger.error(f"Error opening connection dialog: {e}")
            messagebox.showerror("Error", f"Failed to open connection dialog:\n{e}")
    
    def configure_api_keys(self):
        """Open dialog to configure API keys."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure API Keys")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Instructions
        ttk.Label(
            dialog,
            text="Enter your API keys to enable AI-powered image processing:",
            wraplength=450
        ).pack(pady=10)
        
        # Anthropic
        anthropic_frame = ttk.LabelFrame(dialog, text="Anthropic Claude", padding="10")
        anthropic_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(anthropic_frame, text="API Key:").pack(anchor=tk.W)
        anthropic_entry = ttk.Entry(anthropic_frame, width=50, show="*")
        anthropic_entry.pack(fill=tk.X, pady=(5, 0))
        if self.anthropic_api_key:
            anthropic_entry.insert(0, self.anthropic_api_key)
        
        # OpenAI
        openai_frame = ttk.LabelFrame(dialog, text="OpenAI GPT-4", padding="10")
        openai_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(openai_frame, text="API Key:").pack(anchor=tk.W)
        openai_entry = ttk.Entry(openai_frame, width=50, show="*")
        openai_entry.pack(fill=tk.X, pady=(5, 0))
        if self.openai_api_key:
            openai_entry.insert(0, self.openai_api_key)
        
        # Gemini
        gemini_frame = ttk.LabelFrame(dialog, text="Google Gemini", padding="10")
        gemini_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(gemini_frame, text="API Key:").pack(anchor=tk.W)
        gemini_entry = ttk.Entry(gemini_frame, width=50, show="*")
        gemini_entry.pack(fill=tk.X, pady=(5, 0))
        if self.gemini_api_key:
            gemini_entry.insert(0, self.gemini_api_key)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        def save_keys():
            self.anthropic_api_key = anthropic_entry.get().strip() or None
            self.openai_api_key = openai_entry.get().strip() or None
            self.gemini_api_key = gemini_entry.get().strip() or None
            
            # Reinitialize AI generator
            self.ai_generator = None
            
            dialog.destroy()
            messagebox.showinfo("Success", "API keys have been configured")
        
        ttk.Button(btn_frame, text="Save", command=save_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def on_closing(self):
        """Handle window close."""
        # Stop processing
        self.processing_active = False
        
        # Save queue
        self.print_queue.save_to_file(self.queue_file)
        
        # Stop camera
        self.camera_running = False
        if self.camera:
            self.camera.release()
        
        # Close window
        self.root.destroy()


def main():
    """Run the photo booth application."""
    root = tk.Tk()
    app = PhotoBoothApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
