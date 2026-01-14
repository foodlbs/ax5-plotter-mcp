# AX5 Plotter Photo Booth 📸✏️

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](https://www.anthropic.com)

**An interactive AI-powered photo booth that transforms live camera captures into beautiful line art drawings and plots them on an AX5 pen plotter.**

Perfect for events, parties, exhibitions, or just creating unique artistic prints! Choose from multiple artistic styles, powered by state-of-the-art AI models or classic edge detection algorithms.

![Demo](https://img.shields.io/badge/Status-Production_Ready-success)

---

## 🌟 Features

### 📸 Live Camera Experience
- **Real-time Preview**: See yourself before capturing
- **Instant Capture**: One-click photo capture
- **Retake Option**: Get the perfect shot

### 🎨 Six Artistic Styles
Transform your photos into:
- **🎨 Cartoon**: Bold, playful outlines with minimal shading
- **✏️ Sketch**: Hand-drawn artistic look with organic lines
- **💥 Comic**: Dynamic comic book style with strong outlines
- **〰️ Outline**: Pure minimal outlines, no details
- **🖼️ Artistic**: Expressive line art with varied line weights
- **⚪ Minimal**: Ultra-simple lines with elegant simplicity

### 🤖 AI-Powered Processing
Choose your preferred AI provider:
- **Anthropic Claude 3.5**: High-quality, nuanced line art
- **OpenAI GPT-4o**: Advanced vision-based processing
- **Google Gemini 2.5**: Fast and efficient processing
- **Canny Edge Detection**: Classic algorithm (no API key needed)

### 📋 Smart Queue Management
- **Real-time Dashboard**: Monitor all jobs and their status
- **Queue Position Tracking**: Know exactly when your print is coming
- **Status Indicators**: Queued ⏳ → Processing ⚙️ → Plotting 🖨️ → Completed ✅
- **Job Management**: Cancel queued jobs anytime
- **Persistent State**: Queue survives app restarts

### 👤 User Information Capture
- Name and email entry for each photo
- Organized file storage by user
- Each user gets their own folder: `Name_Email/`
- All files timestamped for easy retrieval

### 🖨️ AX5 Plotter Integration
- Direct USB connection to AX5 plotter
- G-code generation and plotting
- Progress tracking during plotting
- Multiple pen profile support

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Webcam** (built-in or USB)
- **AX5 Pen Plotter** (optional, for actual plotting)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ax5-plotter-mcp.git
cd ax5-plotter-mcp
```

2. **Install dependencies**
```bash
pip install -r requirements-simple.txt
```

Required packages:
- `opencv-python` - Camera capture and image processing
- `Pillow` - Image manipulation
- `numpy` - Numerical operations
- `pyyaml` - Configuration management
- `anthropic` - Claude AI integration (optional)
- `openai` - GPT-4 integration (optional)
- `google-generativeai` - Gemini integration (optional)

3. **Configure (Optional)**

Copy the example configuration:
```bash
cp config/settings.example.yaml config/settings.yaml
```

The app works with defaults. Only edit if you need custom plotter settings or want to pre-configure API keys.

4. **Run the Application**
```bash
python photo_booth_app.py
```

---

## 📖 Usage Guide

### Basic Workflow

```
📸 Capture Photo → Enter Info → Choose Style → 🎨 Generate Preview → 🖨️ Add to Queue
```

### Step-by-Step Instructions

#### 1. **Capture a Photo**
   - Position yourself in front of the camera
   - Check the live preview window
   - Click **📸 Capture Photo** when ready
   - Review your captured image
   - Click **🔄 Retake** if you want to try again

#### 2. **Enter Your Information**
   - **Name**: Enter your name
   - **Email**: Enter your email address (used for file organization)

#### 3. **Choose Your Artistic Style**
   - Select one of the 6 styles based on your preference
   - Each style produces different artistic effects
   - Default is **Cartoon** (recommended for portraits)

#### 4. **Select AI Provider (Optional)**
   - **None (Canny)**: Classic edge detection, no API key required ✓
   - **Anthropic Claude**: Best quality, requires API key
   - **OpenAI GPT-4**: Advanced processing, requires API key
   - **Google Gemini**: Fast processing, requires API key
   
   *First time?* Click **Configure API Keys** to enter your keys.

#### 5. **Generate Preview** ⭐
   - Click **🎨 Generate Preview**
   - Wait 10-30 seconds while processing (AI) or 2-3 seconds (Canny)
   - Review the processed line art image
   - If you don't like it, try a different style!

#### 6. **Add to Print Queue**
   - Happy with the preview? Click **🖨️ Add to Print Queue**
   - Your job is now queued for plotting
   - Check the **Queue Dashboard** to monitor progress

### Queue Dashboard

The queue dashboard shows all jobs in real-time:

- **Job ID**: Unique identifier
- **User**: Name and email
- **Style**: Selected artistic style
- **Status**: Current job status
  - ⏳ **Queued**: Waiting in line
  - ⚙️ **Processing**: Being processed right now
  - 🖨️ **Plotting**: Currently plotting on the plotter
  - ✅ **Completed**: Successfully finished
  - ❌ **Failed**: Error occurred
  - 🚫 **Cancelled**: Job was cancelled
- **Actions**: Cancel queued jobs

### File Organization

All outputs are automatically organized:

```
output/
├── captures/                    # Original captured photos
│   └── Name_Email/
│       └── capture_timestamp.jpg
├── processed/                   # Processed line art images
│   └── Name_Email/
│       └── processed_timestamp.png
├── gcode/                       # Generated G-code files
│   └── Name_Email/
│       └── gcode_timestamp.gcode
└── saved_images/               # Additional saved images
```

---

## 🎨 Style Guide

### When to Use Each Style

**🎨 Cartoon** (Recommended for portraits)
- Best for: Faces, people, casual photos
- Effect: Playful, bold outlines with character
- Processing: Medium thickness lines

**✏️ Sketch**
- Best for: Artistic portraits, nature
- Effect: Hand-drawn, organic feel
- Processing: Varied line weights

**💥 Comic**
- Best for: Action shots, dynamic poses
- Effect: Bold comic book style
- Processing: Strong black outlines

**〰️ Outline**
- Best for: Logos, simple objects
- Effect: Clean, minimal outlines only
- Processing: Thin, precise lines

**🖼️ Artistic**
- Best for: Creative portraits, expressive images
- Effect: Fine art style with varied lines
- Processing: Complex line work

**⚪ Minimal**
- Best for: Modern aesthetic, simple subjects
- Effect: Ultra-simple, elegant
- Processing: Very thin, selective lines

---

## 🔧 Configuration

### API Keys

You can configure API keys in two ways:

**Method 1: Through the UI** (Recommended)
1. Click **Configure API Keys** in the app
2. Enter your API key(s)
3. Click Save

**Method 2: Config File**
1. Edit `config/settings.yaml`
2. Add your keys under `ai.api_keys`:
```yaml
ai:
  api_keys:
    anthropic: "your-key-here"
    openai: "your-key-here"
    gemini: "your-key-here"
```

### Get API Keys

- **Anthropic Claude**: https://console.anthropic.com/
- **OpenAI GPT-4**: https://platform.openai.com/
- **Google Gemini**: https://aistudio.google.com/

### Plotter Configuration

Edit `config/settings.yaml` to configure your AX5 plotter:

```yaml
plotter:
  port: /dev/cu.usbserial-0001  # Your serial port
  baud: 115200
  width: 210   # mm (A5 size)
  height: 150  # mm
  margin: 10   # mm

servo:
  pen_up: "M3 S90"    # Pen lift command
  pen_down: "M5"       # Pen down command

speeds:
  travel: 3000   # Fast movement (mm/min)
  draw: 500      # Drawing speed (mm/min)
```

**Finding your serial port:**
- **macOS**: `/dev/cu.usbserial-*` or `/dev/tty.usbserial-*`
- **Linux**: `/dev/ttyUSB0` or `/dev/ttyACM0`
- **Windows**: `COM3`, `COM4`, etc.

---

## 🛠️ Advanced Features

### Preview Before Queue

The app uses a **2-step workflow** to ensure you're happy with the result:

1. **Generate Preview**: See the processed image first
2. **Add to Queue**: Only queue it if you like it

This prevents wasting time and paper on results you don't want!

### Queue Persistence

The print queue is saved to `queue_state.json` and persists between app restarts. If you close the app, your queued jobs will still be there when you restart.

### Testing Without Plotter

You can use the app without a physical plotter connected:
- Capture photos ✓
- Generate previews ✓
- Add to queue ✓
- Files are saved and organized ✓
- Actual plotting is skipped

Perfect for testing or running the photo booth without hardware!

---

## 📂 Project Structure

```
ax5-plotter-mcp/
├── photo_booth_app.py          # Main application
├── test_photo_booth.py         # End-to-end test suite
├── requirements-simple.txt     # Python dependencies
├── config/
│   ├── settings.yaml           # User configuration
│   └── settings.example.yaml   # Example configuration
├── src/
│   ├── plotter/
│   │   ├── ax5.py             # AX5 plotter controller
│   │   ├── grbl.py            # GRBL interface
│   │   └── interface.py       # Plotter interface
│   └── utils/
│       ├── ai_caricature_generator.py  # AI & edge detection
│       ├── print_queue.py     # Queue management
│       └── svg_converter.py   # SVG to G-code conversion
├── output/
│   ├── captures/              # Original photos
│   ├── processed/             # Processed images
│   ├── gcode/                 # G-code files
│   └── saved_images/          # Additional saves
├── logs/                      # Application logs
└── docs/                      # Additional documentation
```

---

## 🐛 Troubleshooting

### Camera Issues

**Problem**: Camera won't start
```
Error: Could not start webcam
```

**Solutions**:
- Check webcam is connected and working
- Close other apps using the camera (Zoom, Skype, etc.)
- Try a different camera by editing the camera index in code
- On macOS: Grant camera permissions in System Preferences → Security & Privacy
- On Linux: Check permissions for `/dev/video0`

### API Key Issues

**Problem**: AI processing fails
```
Error: Invalid API key
```

**Solutions**:
- Verify your API key is correct
- Check you have credits/quota remaining
- Try using Canny (no API key required)
- Reconfigure via **Configure API Keys** button

### Plotter Connection Issues

**Problem**: Plotter won't connect
```
Error: Could not connect to plotter
```

**Solutions**:
- Check USB cable is connected
- Verify the correct port in `config/settings.yaml`
- Ensure no other software is using the serial port
- On Linux: Add user to `dialout` group: `sudo usermod -a -G dialout $USER`
- Try unplugging and replugging the plotter
- Restart the application

### Processing Issues

**Problem**: Preview shows poor results

**Solutions**:
- Try a different artistic style
- Use AI processing instead of Canny (or vice versa)
- Ensure good lighting on your subject
- Retake the photo with better contrast
- Use a different AI provider

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_photo_booth.py
```

This will test:
- ✓ Module imports
- ✓ Camera capture
- ✓ Image processing (Canny)
- ✓ AI processing (if configured)
- ✓ Queue management
- ✓ G-code generation
- ✓ File organization

---

## 🎯 Use Cases

### Event Photo Booth
Set up at weddings, parties, or corporate events. Guests take photos and receive unique artistic prints as keepsakes.

### Art Exhibitions
Create live art at galleries or maker fairs. Show the transformation from photo to line art to physical plot.

### Educational Demos
Demonstrate computer vision, AI, and robotics integration in STEM education.

### Personalized Gifts
Create custom portrait drawings for gifts, merchandise, or commissions.

---

## 📝 Tips for Best Results

### Photography Tips
- **Lighting**: Ensure good, even lighting on your subject
- **Contrast**: Clear light/dark boundaries work best
- **Background**: Plain backgrounds produce cleaner results
- **Distance**: Position yourself 2-3 feet from camera
- **Expression**: Smile! Exaggerated expressions work great

### Style Selection
- **Portraits**: Cartoon or Sketch styles
- **Logos/Graphics**: Outline or Minimal styles
- **Action**: Comic style
- **Artistic**: Artistic or Sketch styles

### AI vs Canny
- **Canny**: Fast (2-3 seconds), free, good for simple images
- **AI**: Slower (10-30 seconds), requires API key, handles complex images better, more artistic interpretation

---

## 🤝 Contributing

This is a showcase project, but suggestions and improvements are welcome! Feel free to:
- Report bugs
- Suggest new features
- Improve documentation
- Add new artistic styles

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Rahul Patel**

Created as a demonstration of integrating computer vision, AI, and hardware control into a cohesive interactive application.

---

## 🙏 Acknowledgments

- **Anthropic Claude** - High-quality AI processing
- **OpenAI GPT-4** - Vision-based image understanding
- **Google Gemini** - Fast AI processing
- **OpenCV** - Computer vision and edge detection
- **AX5 Plotter** - Hardware platform

---

## 📚 Additional Documentation

For detailed technical information, see the [docs/](docs/) folder:
- [CHANGELOG.md](docs/CHANGELOG.md) - Version history and updates
- [IMAGE_PROCESSING_UPDATE.md](docs/IMAGE_PROCESSING_UPDATE.md) - Technical details on image processing
- [NEW_PREVIEW_WORKFLOW.md](docs/NEW_PREVIEW_WORKFLOW.md) - Preview workflow documentation

---

**Ready to create amazing pen plotter art? Get started now!** 🚀

```bash
python photo_booth_app.py
```
