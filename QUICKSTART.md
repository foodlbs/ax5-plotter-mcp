# Quick Start Guide 🚀

**Get the AX5 Plotter Photo Booth running in 5 minutes!**

## Prerequisites Check

Before starting, ensure you have:
- ✓ Python 3.8 or higher installed
- ✓ A webcam (built-in or USB)
- ✓ Basic terminal/command line knowledge

## Installation (3 minutes)

### Step 1: Clone & Navigate
```bash
git clone https://github.com/yourusername/ax5-plotter-mcp.git
cd ax5-plotter-mcp
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- OpenCV for camera and image processing
- Pillow for image manipulation
- NumPy for numerical operations
- PyYAML for configuration
- Optional AI libraries (Anthropic, OpenAI, Google)

### Step 3: Launch!
```bash
python photo_booth_app.py
```

That's it! The app should open with your camera preview.

## First Use (2 minutes)

### 1. Take Your First Photo
- Look at the camera preview
- Click **📸 Capture Photo**
- See your captured image

### 2. Fill in Details
- **Name**: Your name
- **Email**: your@email.com

### 3. Choose a Style
- Start with **🎨 Cartoon** (it's great for faces!)

### 4. Select Processing
- Choose **None (Canny)** for now
- No API key needed!

### 5. Generate & Review
- Click **🎨 Generate Preview**
- Wait 2-3 seconds
- See your photo transformed to line art!

### 6. Queue It Up
- Like it? Click **🖨️ Add to Print Queue**
- Done! Your first print job is queued

## What Just Happened?

Your photo was:
1. Captured from your webcam ✓
2. Processed into line art ✓
3. Saved to `output/captures/` and `output/processed/` ✓
4. Added to the print queue ✓

Check the **Queue Dashboard** tab to see your job!

## Next Steps

### Try Different Styles
Each style creates a different artistic effect:
- **Cartoon**: Bold, playful (great for portraits)
- **Sketch**: Hand-drawn feel
- **Comic**: Strong comic book style
- **Outline**: Minimal clean lines
- **Artistic**: Fine art style
- **Minimal**: Ultra-simple elegant

### Try AI Processing (Optional)

For better results with complex images:

1. Get an API key from:
   - [Anthropic Claude](https://console.anthropic.com/) (recommended)
   - [OpenAI GPT-4](https://platform.openai.com/)
   - [Google Gemini](https://aistudio.google.com/)

2. Click **Configure API Keys** in the app

3. Enter your key and save

4. Select the AI provider from the dropdown

5. Generate preview - it takes 10-30 seconds but produces better results!

### Connect Your Plotter (Optional)

If you have an AX5 plotter:

1. Connect it via USB
2. Edit `config/settings.yaml`:
   ```yaml
   plotter:
     port: /dev/cu.usbserial-0001  # Your serial port
   ```
3. The app will automatically plot queued jobs!

## Common Issues

### "Camera not found"
- Check camera is connected
- Close other apps using the camera (Zoom, Skype, etc.)
- Try granting camera permissions in system settings

### "Module not found" errors
- Run: `pip install -r requirements.txt`
- Make sure you're using Python 3.8+: `python --version`

### Can't see processed image
- Check the `output/processed/` folder
- Images are saved even if preview fails

## Files You'll See

After your first use:

```
output/
├── captures/Name_Email/capture_*.jpg      ← Your original photo
├── processed/Name_Email/processed_*.png   ← Line art version
└── gcode/Name_Email/gcode_*.gcode        ← G-code (if using plotter)
```

## Performance Tips

**Fast Processing (2-3 seconds):**
- Use Canny edge detection
- No API key needed
- Good for simple images

**Best Quality (10-30 seconds):**
- Use AI (Claude, GPT-4, or Gemini)
- Requires API key
- Handles complex images better
- More artistic interpretation

## You're Ready!

Now you can:
- ✓ Capture photos with your webcam
- ✓ Transform them to line art
- ✓ Try different artistic styles
- ✓ Manage a print queue
- ✓ Organize files by user

**Want more details?** Check out the main [README.md](README.md) for comprehensive documentation.

**Ready for advanced features?** See the [docs/](docs/) folder for technical deep-dives.

## Showcase This Project

Perfect for demonstrating:
- 🎨 Computer vision & image processing
- 🤖 AI integration (multiple providers)
- 🖨️ Hardware control (plotter)
- 📋 Queue management systems
- 💻 Interactive UI with Tkinter
- 📁 File organization & persistence

Add this to your portfolio, show it at maker fairs, or use it at events!

---

**Questions or issues?** Open an issue on GitHub or check [CONTRIBUTING.md](CONTRIBUTING.md)
