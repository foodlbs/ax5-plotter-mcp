# AX5 Plotter Photo Booth

An interactive photo booth application for the AX5 plotter with live camera preview, multiple artistic styles, queue management, and organized file storage.

## Features

### 📸 Live Camera Experience
- **Live Preview**: Real-time camera feed before capture
- **Instant Capture**: Take photos with a single click
- **Retake Option**: Perfect your shot before adding to queue

### 🎨 Multiple Artistic Styles
Choose from 6 different image processing styles:

- **🎨 Cartoon**: Bold, playful outlines with minimal shading
- **✏️ Sketch**: Artistic hand-drawn look with organic lines
- **💥 Comic**: Dynamic comic book style with strong black outlines
- **〰️ Outline**: Pure minimal outlines, no details
- **🖼️ Artistic**: Expressive line art with varied line weights
- **⚪ Minimal**: Ultra-simple lines with elegant simplicity

### 🤖 AI-Powered Processing
- **Anthropic Claude**: High-quality AI-generated line art
- **OpenAI GPT-4**: Advanced vision-based processing
- **Google Gemini**: Fast and efficient AI processing
- **Canny Edge Detection**: Classic algorithm (no API key needed)

### 👤 User Information Capture
- Name and email entry for each photo
- Organized file storage by user
- Personalized confirmation messages

### 📋 Print Queue System
- **Real-time Dashboard**: See all jobs and their status
- **Queue Position**: Know exactly when your print is coming
- **Status Tracking**: 
  - ⏳ Queued
  - ⚙️ Processing
  - 🖨️ Plotting
  - ✅ Completed
  - ❌ Failed
  - 🚫 Cancelled
- **Queue Management**: Cancel queued jobs
- **Persistent State**: Queue survives app restarts

### � Organized File Storage
- Each user gets their own folder
- Folder named: `Name_Email`
- Contains processed image and G-code
- Easy to find and retrieve files
- All files timestamped

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements-simple.txt

# Additional photo booth dependencies
pip install pyyaml
```

### Configuration

1. **Copy example config** (optional):
```bash
cp config/settings.example.yaml config/settings.yaml
```

The app will work with default settings. Configuration is only needed for custom plotter settings.

### Run the Application

```bash
python photo_booth_app.py
```

## Usage Guide

### 1. Capture a Photo
1. Position yourself in front of the camera
2. Check the live preview
3. Click **📸 Capture Photo** when ready
4. Review the captured image
5. Click **🔄 Retake** if needed

### 2. Enter Your Information
1. Enter your **Name**
2. Enter your **Email** (to receive the processed image)

### 3. Choose Your Style
Select one of the 6 artistic styles based on your preference.

### 4. Select AI Provider (Optional)
- Choose **None (Canny)** for classic edge detection (no API key required)
- Choose **Anthropic Claude**, **OpenAI GPT-4**, or **Google Gemini** for AI processing
- Click **Configure API Keys** to enter your API keys

### 5. Add to Queue
1. Click **🖨️ Add to Print Queue**
2. See your queue position and folder location
3. Monitor progress in the dashboard

### 6. Find Your Files
- Check the folder shown in the confirmation message
- Location: `output/saved_images/YourName_YourEmail/`
- Contains: processed image and G-code file
- Files are timestamped for organization

## Queue Dashboard

The dashboard shows:
- **Total Statistics**: Queued, Processing, and Completed counts
- **Job List**: All jobs with name, style, status, and time
- **Real-time Updates**: Automatically refreshes as jobs progress

### Queue Controls
- **Cancel Selected**: Cancel a queued job (only before processing starts)
- **Refresh**: Manually refresh the dashboard

## API Keys Setup

### Anthropic Claude
1. Sign up at [anthropic.com](https://www.anthropic.com/)
2. Generate an API key
3. Click **Configure API Keys** in the app
4. Enter your key in the Anthropic Claude section

### OpenAI GPT-4
1. Sign up at [platform.openai.com](https://platform.openai.com/)
2. Generate an API key
3. Click **Configure API Keys** in the app
4. Enter your key in the OpenAI GPT-4 section

### Google Gemini
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **Configure API Keys** in the app
3. Enter your key in the Google Gemini section

## How It Works

### Processing Pipeline
1. **Capture**: Photo taken from webcam
2. **Queue**: Job added with user info and style preference
3. **Processing**: 
   - AI generates artistic interpretation (if provider selected)
   - Or Canny edge detection applied
4. **G-code Generation**: Processed image converted to plotter commands
5. **File Storage**: Files saved to organized user folder
6. **Complete**: Status updated in dashboard

### Background Processing
- Jobs are processed in the background automatically
- Multiple jobs can be queued
- Processing continues even while capturing new photos
- Queue state persists between app sessions

## File Structure

```
output/
├── captures/                    # Original captured photos
├── processed/                   # Temp processed images
├── gcode/                      # Temp G-code files
└── saved_images/               # Organized user folders
    ├── John_Doe_john_at_email_com/
    │   ├── cartoon_20231113_143022.png
    │   └── cartoon_20231113_143022.gcode
    ├── Jane_Smith_jane_at_email_com/
    │   ├── sketch_20231113_143156.png
    │   └── sketch_20231113_143156.gcode
    └── ...

queue_state.json                # Persistent queue state
```

Each user folder contains:
- Processed image file (PNG)
- G-code file (for plotter)
- Named with style and timestamp

## Troubleshooting

### Camera Issues
**Problem**: Camera not detected
**Solution**: 
- Check camera permissions
- Try a different camera index in the code (change `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)`)

### Finding Your Files
**Problem**: Can't find processed images
**Solution**:
- Look in `output/saved_images/YourName_YourEmail/`
- Check the confirmation dialog for exact path
- Folder names replace spaces and special characters

### AI Processing Fails
**Problem**: AI provider returns errors
**Solution**:
- Verify API key is correct
- Check API key has sufficient credits
- Try a different AI provider
- Use "None (Canny)" as fallback (always works)

### Queue Not Processing
**Problem**: Jobs stay in "Queued" status
**Solution**:
- Check logs for error messages
- Restart the application
- Check `queue_state.json` for corrupted data

## Advanced Configuration

### Style Customization
Edit `STYLE_PROMPTS` in `photo_booth_app.py` to customize AI prompts for each style.

### Processing Parameters
Adjust edge detection in `process_job()`:
```python
processed_img = cv2.Canny(gray, 50, 150)  # Adjust thresholds
```

### Queue Persistence
Queue state is automatically saved to `queue_state.json`:
- Jobs survive app restarts
- Failed jobs can be retried manually
- Delete file to clear all history

## Tips for Best Results

### Photography
- Good lighting is essential
- Position face centered in frame
- Avoid busy backgrounds
- Keep still during capture

### Style Selection
- **Cartoon**: Best for portraits with clear features
- **Sketch**: Great for artistic, expressive looks
- **Comic**: Works well with dramatic lighting
- **Outline**: Best for clean, minimal aesthetics
- **Artistic**: Good for varied textures
- **Minimal**: Perfect for iconic, simplified portraits

### AI Providers
- **Anthropic Claude**: Best overall quality, most detailed
- **OpenAI GPT-4**: Great for creative interpretations
- **Google Gemini**: Fast processing, good results
- **Canny**: Instant results, no API costs

## Event Setup Guide

### For Public Events
1. **Setup**:
   - Position camera at eye level
   - Ensure good front lighting
   - Test focus and framing
   - Load test print to verify plotter

2. **Configure**:
   - Set email to enabled
   - Prepare backup plotter (if available)
   - Clear old queue: `rm queue_state.json`

3. **Operation**:
   - One person manages app
   - Guide users through steps
   - Monitor queue dashboard
   - Handle plotter paper/pen

4. **Best Practices**:
   - Keep API keys secure
   - Monitor API usage/costs
   - Have backup power
   - Print test sample for display

## License

Same as main AX5 Plotter project.

## Support

For issues or questions:
1. Check this README
2. Review logs in console
3. Check queue_state.json for job details
4. Open an issue on GitHub
