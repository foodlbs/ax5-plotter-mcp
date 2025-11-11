# Simple AX5 Plotter Local Application

This is a simplified local application for the AX5 plotter that allows you to:
- Upload image files (JPEG, PNG, etc.)
- Capture photos using your webcam
- Convert images to line drawings/sketches
- Plot them directly on your AX5 plotter

## Features

### Image Input
- **File Upload**: Support for JPEG, PNG, BMP, TIFF, GIF formats
- **Webcam Capture**: Live webcam preview and image capture
- **Image Preview**: See your selected/captured image before processing

### Image Processing
- **Edge Detection Methods**:
  - Canny Edge Detection (recommended)
  - Laplacian Edge Detection
  - Sobel Edge Detection  
  - Contour Detection
- **Adjustable Parameters**:
  - Threshold controls for fine-tuning edge detection
  - Blur settings for smoothing
  - Invert option for white/black backgrounds
- **Real-time Preview**: See processing results before plotting

### Plotter Integration
- **Direct Connection**: Connect to AX5 plotter via USB
- **Plotter Control**: Home, pen up/down testing
- **Pen Profiles**: Choose from marker, ballpoint, fountain pen settings
- **Progress Tracking**: Live plotting progress with progress bar

## Quick Setup

### 1. Install Dependencies

```bash
# Install Python dependencies for the simple app
pip install -r requirements-simple.txt
```

### 2. Configure Your Plotter

Copy the example configuration and edit for your setup:

```bash
cp config/settings.example.yaml config/settings.yaml
```

Edit `config/settings.yaml` and update:
- `plotter.port`: Your Arduino port (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, or `COM3`)
- Other settings as needed for your specific setup

### 3. Connect Hardware

1. Connect your AX5 plotter via USB
2. Ensure it's powered on and recognized by your system
3. Load paper and install pen

### 4. Run the Application

```bash
python simple_plotter_app.py
```

## Usage Guide

### Basic Workflow

1. **Start the Application**
   ```bash
   python simple_plotter_app.py
   ```

2. **Load an Image**
   - **File Upload**: Click "Select Image File" in the Image Input tab
   - **Webcam**: Click "Start Webcam" then "Capture Image"

3. **Process the Image**
   - Go to the "Image Processing" tab
   - Choose edge detection method (Canny is recommended for most photos)
   - Adjust thresholds and blur settings
   - Check "Invert" for white background sketches
   - Click "Process Image" to see the result

4. **Connect Plotter**
   - Go to the "Plotter Control" tab
   - Click "Connect Plotter"
   - Optionally click "Home Plotter" to calibrate

5. **Plot Your Sketch**
   - Choose pen profile (ballpoint, marker, fountain)
   - Click "Plot Current Image"
   - Watch the progress bar for plotting status

### Tips for Best Results

#### Image Selection
- **Good contrast**: Images with clear light/dark boundaries work best
- **Simple subjects**: Portraits, buildings, objects with clear outlines
- **Avoid**: Very busy/detailed images, low contrast, or blurry photos

#### Processing Settings
- **Canny Method**: Best for most photos, portraits
  - Lower Threshold 1 (30-70) for thicker lines
  - Higher Threshold 2 (100-200) for cleaner edges
- **Contour Method**: Good for high-contrast images, logos
- **Blur**: Use 1-3 for photos, higher for noisy images
- **Invert**: Enable for dark sketches on white paper

#### Plotter Settings
- **Marker**: Fast plotting, thick lines
- **Ballpoint**: Good balance of speed and quality  
- **Fountain**: Slower but highest quality, variable line width

## Troubleshooting

### Connection Issues
```
Error: Could not connect to plotter
```
- Check USB connection and cable
- Verify port in `config/settings.yaml` (try `/dev/ttyACM0` if `/dev/ttyUSB0` doesn't work)
- Check that no other software is using the serial port
- On Linux: ensure user is in `dialout` group
- Restart plotter and try again

### Webcam Issues
```
Error: Could not start webcam  
```
- Ensure webcam is connected and working
- Try a different camera index (edit the `camera_index` in code if needed)
- Close other applications using the webcam
- On Linux: check permissions for `/dev/video0`

### Image Processing Issues
- **No edges detected**: Try lowering Threshold 1, increasing blur
- **Too many lines**: Increase both thresholds, try Canny method
- **Poor quality**: Use higher resolution input image, adjust blur

### Plotting Issues
- **Pen doesn't move**: Check pen up/down commands in config
- **Wrong positioning**: Run homing cycle first
- **Lines too light**: Adjust pen profile, check pen ink
- **Plot interrupted**: Check serial connection, reduce plotting speed in config

## Configuration

The application uses the same configuration as the full AX5 plotter system. Key settings:

```yaml
# config/settings.yaml
plotter:
  port: /dev/ttyUSB0    # Your Arduino port
  dimensions:
    width: 210          # Plotting area width (mm)  
    height: 150         # Plotting area height (mm)

servo:
  pen_up_command: "M3 S90"     # Pen lift command
  pen_down_command: "M5"        # Pen down command
  
speeds:
  travel: 3000         # Fast movement speed
  draw: 500           # Drawing speed
```

## Advanced Usage

### Custom Image Processing
You can modify the image processing by editing the `ImageProcessor` class in `simple_plotter_app.py`. Add new methods or adjust existing ones for your specific needs.

### Batch Processing
For multiple images, you can modify the application or use the command-line tools from the main project.

### Integration with Main System
This simple app can run alongside the full MCP server system. Just ensure they don't try to connect to the plotter simultaneously.

## Safety Notes

- Always ensure the plotter workspace is clear before starting
- Keep the emergency stop accessible
- Monitor the first few plots to ensure proper operation
- Use appropriate paper size for your plotter dimensions

## Support

For issues specific to this simple application:
1. Check the troubleshooting section above
2. Verify your configuration matches your hardware
3. Test with the basic examples in the main project first
4. Check the logs for detailed error messages

For general AX5 plotter support, refer to the main project documentation.