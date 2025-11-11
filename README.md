# AX5 Plotter - Simple Local Application# AX5 Plotter MCP Server (Public Edition)



**Simple desktop application for converting photos to sketches and plotting them on your AX5 pen plotter.****Model Context Protocol (MCP) server for intelligent control of AX5 pen plotter with CoreXY kinematics and GRBL 0.9 firmware.**



![AX5 Plotter](https://img.shields.io/badge/Hardware-AX5_Plotter-blue)This project provides a complete plotter control system with:

![Python](https://img.shields.io/badge/Python-3.8+-green)- 🔐 **Authentication & User Management** - Multi-user support with JWT/API key auth

![License](https://img.shields.io/badge/License-MIT-yellow)- 🌐 **Public Internet Access** - Deploy as internet-accessible service with SSL

- 🤖 **MCP Integration** - AI-assisted plotter control via Model Context Protocol

## Features- 🌐 **REST API** - FastAPI-based web interface for job submission and monitoring

- 📊 **Real-time Progress** - Server-Sent Events (SSE) for live job updates

🖼️ **Image Input**- 🔄 **Job Queue** - Redis Queue (RQ) for reliable job processing

- Upload photos (JPEG, PNG, BMP, TIFF, GIF)- 📐 **SVG Conversion** - Optimized G-code generation with path optimization

- Live webcam capture with preview- 🎯 **CoreXY Support** - Native support for AX5 CoreXY kinematics

- Drag & drop support- 🖊️ **Servo Control** - Pen up/down via modified GRBL firmware

- ⚡ **Rate Limiting** - Prevent abuse with per-user quotas

🎨 **Image Processing**- 👥 **Admin Panel** - Manage users and monitor usage

- 4 edge detection methods (Canny, Laplacian, Sobel, Contours)

- Real-time preview of sketch conversion## 🆕 Simple Local Application

- Adjustable thresholds, blur, and invert options

- Automatic SVG vectorization**NEW**: For a simple, easy-to-use local application that can convert photos to sketches and plot them directly, see [**SIMPLE_APP_README.md**](SIMPLE_APP_README.md).



🖨️ **Direct Plotting**The simple app provides:

- One-click plotting to AX5 plotter- 📷 **Photo Upload & Webcam Capture** - Load images or capture from webcam

- Multiple pen profiles (marker, ballpoint, fountain)- 🖼️ **Image to Sketch Conversion** - Multiple edge detection methods

- Live progress tracking- 🎨 **Real-time Preview** - See your sketch before plotting  

- Pen up/down testing- 🖨️ **Direct Plotting** - Plot immediately with one click

- Homing controls- 🔧 **Easy Setup** - Minimal dependencies, simple GUI



## Hardware Requirements**Quick Start Simple App:**

```bash

- **AX5 Pen Plotter** with CoreXY kinematics./launch_simple_app.sh    # Linux/macOS

- **Arduino UNO** running GRBL 0.9i with servo supportlaunch_simple_app.bat     # Windows

- **USB connection** from computer to Arduino```

- **Webcam** (optional, for photo capture)

## Hardware Requirements

## Quick Start

- **AX5 Pen Plotter** with CoreXY kinematics

### 1. Install Dependencies- **Arduino UNO** running GRBL 0.9i with servo support

- **ZimaBoard 832** or similar Linux SBC (specs below)

```bash- USB connection from server to Arduino

# Install Python dependencies

pip install -r requirements-simple.txt### ZimaBoard 832 Compatibility ✅

```

This server is fully compatible with ZimaBoard 832:

### 2. Configure Plotter- **CPU**: Intel Celeron N3450 (quad-core x86) - ✅ Sufficient

- **RAM**: 8GB - ✅ More than adequate (2GB minimum)

Copy and edit the configuration file:- **Storage**: 32GB eMMC - ✅ Plenty for OS + server + job storage

- **USB**: Multiple USB 3.0 ports - ✅ For Arduino connection

```bash- **OS**: Ubuntu/Debian Linux - ✅ Fully supported

cp config/settings.example.yaml config/settings.yaml

```## Quick Start



Edit `config/settings.yaml` and update:### Local Deployment (Single User)

- `plotter.port`: Your Arduino port (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, or `COM3`)

- Other settings as needed for your setup```bash

# On ZimaBoard or any Linux system

### 3. Connect Hardwaresudo apt update

sudo apt install -y python3.11 python3-pip redis-server

1. Connect AX5 plotter via USB

2. Ensure it's powered on# Install uv (recommended) or pip

3. Load paper and install pencurl -LsSf https://astral.sh/uv/install.sh | sh



### 4. Launch Application# Install Python dependencies

uv venv

**Linux/macOS:**source .venv/bin/activate

```bashuv pip install -r requirements.txt

./launch_simple_app.sh```

```

### Public Deployment (Multi-User, Internet-Accessible)

**Windows:**

```bash**⚠️ For internet-accessible deployment with authentication:**

launch_simple_app.bat

```See **[Public Server Deployment Guide](docs/public_server_deployment.md)** for complete instructions including:

- SSL/HTTPS setup with Let's Encrypt

**Or directly:**- Nginx reverse proxy configuration

```bash- User authentication system

python simple_plotter_app.py- Rate limiting and security

```- Domain configuration



## Usage Guide**Quick summary:**

```bash

### Basic Workflow# 1. Setup domain and SSL

sudo certbot --nginx -d your-plotter.com

1. **Load Image**

   - Click "Select Image File" to upload a photo# 2. Configure authentication

   - OR click "Start Webcam" then "Capture Image"cp config/settings.example.yaml config/settings.yaml

nano config/settings.yaml  # Set auth.enabled=true

2. **Process Image**

   - Go to "Image Processing" tab# 3. Start services

   - Choose edge detection method (Canny recommended)sudo systemctl enable ax5-api ax5-worker nginx

   - Adjust thresholds and blur settingssudo systemctl start ax5-api ax5-worker nginx

   - Click "Process Image" to see result

# 4. Access at https://your-plotter.com

3. **Connect Plotter**```

   - Go to "Plotter Control" tab

   - Click "Connect Plotter"### 2. Configure GRBL Firmware

   - Optionally run "Home Plotter"

Flash your Arduino with GRBL 0.9i servo-enabled firmware:

4. **Plot**- Recommended: [arnabdasbwn/grbl-coreXY-servo](https://github.com/arnabdasbwn/grbl-coreXY-servo)

   - Choose pen profile- Alternative: [cojarbi/grbl-servo-CoreXY](https://github.com/cojarbi/grbl-servo-CoreXY)

   - Click "Plot Current Image"

   - Watch progress bar### 3. Configure Settings



### Command Line Tool```bash

# Copy example configuration

For batch processing or automation:cp config/settings.example.yaml config/settings.yaml



```bash# Edit with your serial port

# Convert image and previewnano config/settings.yaml

python simple_converter.py photo.jpg --preview```



# Convert and plot directly### 4. Start Services

python simple_converter.py photo.jpg --plot --pen marker

```bash

# Adjust processing settings# Start Redis

python simple_converter.py photo.jpg --method canny --threshold1 50 --threshold2 150sudo systemctl start redis-server

```

# Start API server

### Tips for Best Resultsuvicorn src.api.main:app --host 0.0.0.0 --port 8000



**Image Selection:**# Start RQ worker (in another terminal)

- High contrast images work bestpython src/workers/plot_worker.py

- Clear subjects (portraits, buildings, objects)

- Avoid very busy or blurry images# Or use systemd services (see docs/deployment.md)

```

**Processing Settings:**

- **Canny**: Best for photos and portraits### 5. Test MCP Server

  - Lower Threshold 1 (30-70) = thicker lines

  - Higher Threshold 2 (100-200) = cleaner edges```bash

- **Contours**: Good for logos and high-contrast images# Install in Claude Desktop

- **Blur**: Use 1-3 for photos, higher for noisy imagesuv run mcp install src/mcp_server/ax5_mcp.py --name "AX5 Plotter"

- **Invert**: Enable for dark sketches on white paper

# Or test with MCP Inspector

**Plotter Settings:**uv run mcp dev src/mcp_server/ax5_mcp.py

- **Marker**: Fast plotting, thick lines```

- **Ballpoint**: Good balance of speed and quality

- **Fountain**: Slower but highest quality## Project Structure



## Troubleshooting```

ax5-plotter-mcp/

### Connection Issues├── src/

│   ├── mcp_server/         # MCP server implementation

**Error: Could not connect to plotter**│   │   ├── ax5_mcp.py      # Main MCP server

- Check USB cable and connection│   │   └── tools.py        # MCP tool definitions

- Verify port in `config/settings.yaml`│   ├── api/                # FastAPI REST API

- Try `/dev/ttyACM0` if `/dev/ttyUSB0` doesn't work│   │   ├── main.py         # API server

- Ensure no other software is using the serial port│   │   └── routes/         # API endpoints

- On Linux: Add user to `dialout` group: `sudo usermod -a -G dialout $USER`│   ├── plotter/            # Hardware abstraction

- Restart plotter and try again│   │   ├── interface.py    # Abstract plotter interface

│   │   ├── ax5.py          # AX5 implementation

### Webcam Issues│   │   └── grbl.py         # GRBL communication

│   ├── workers/            # Background job workers

**Error: Could not start webcam**│   │   └── plot_worker.py  # RQ worker for plot jobs

- Ensure webcam is connected│   └── utils/              # Utilities

- Close other apps using the webcam│       ├── svg_converter.py

- On Linux: Check permissions for `/dev/video0`│       ├── gcode_generator.py

- Try different camera (edit `camera_index` if needed)│       └── path_optimizer.py

├── config/                 # Configuration files

### Image Processing Issues│   ├── settings.yaml

│   └── grbl_profiles/

- **No edges detected**: Lower Threshold 1, increase blur├── tests/                  # Test suite

- **Too many lines**: Increase both thresholds, use Canny├── docs/                   # Documentation

- **Poor quality**: Use higher resolution input, adjust blur├── scripts/                # Deployment scripts

└── uploads/                # SVG file uploads

### Plotting Issues```



- **Pen doesn't move**: Check pen commands in config## API Endpoints

- **Wrong positioning**: Run homing cycle first

- **Lines too light**: Adjust pen profile or check ink### Authentication (Public Server)

- **Plot interrupted**: Check serial connection

When `auth.enabled=true` in config:

## Configuration

**Register:**

Key settings in `config/settings.yaml`:- `POST /api/auth/register` - Create new account

- `POST /api/auth/login` - Get JWT token

```yaml- `GET /api/auth/me` - Get current user info

plotter:- `POST /api/auth/change-password` - Change password

  port: /dev/ttyUSB0    # Your Arduino port- `POST /api/auth/regenerate-api-key` - Get new API key

  baud: 115200

  dimensions:**Admin:**

    width: 210          # Plotting area (mm)- `GET /api/auth/users` - List all users (admin only)

    height: 150- `PATCH /api/auth/users/{id}` - Modify user (admin only)

    margin: 10- `DELETE /api/auth/users/{id}` - Delete user (admin only)



servo:### Plot Management

  pen_up_command: "M3 S90"- `POST /api/plots` - Submit plot job (requires auth if enabled)

  pen_down_command: "M5"- `POST /api/plots/upload` - Upload SVG file (requires auth if enabled)

  dwell_time: 0.15- `GET /api/plots/{id}` - Get job status

  - `GET /api/plots/{id}/stream` - SSE progress stream

  profiles:- `DELETE /api/plots/{id}` - Cancel job

    marker:- `GET /api/plots` - List all jobs

      dwell: 0.1

      speed: 800### Plotter Control

    ballpoint:- `POST /api/plotter/home` - Home plotter

      dwell: 0.15- `GET /api/plotter/status` - Get current status

      speed: 500- `POST /api/plotter/pen` - Manual pen control

    fountain:

      dwell: 0.2## MCP Tools

      speed: 300

When using Claude Desktop or other MCP clients:

speeds:

  travel: 3000         # Fast movement (mm/min)- `get_plotter_status()` - Check plotter state and position

  draw: 500           # Drawing speed- `submit_plot_job(svg_file, priority)` - Queue SVG for plotting

  homing: 2000        # Homing speed- `cancel_job(job_id)` - Stop running job

```- `home_plotter()` - Execute homing cycle

- `list_jobs(status)` - View job queue

## Testing

## Configuration

Run the test suite to verify installation:

Edit `config/settings.yaml`:

```bash

python test_simple_app.py```yaml

```plotter:

  port: /dev/ttyUSB0  # Serial port for Arduino

This checks:  baud: 115200

- Required Python packages  dimensions:

- Configuration files    width: 210   # A5 width (mm)

- Image processing pipeline    height: 150  # A5 height (mm)

- File structure  

servo:

## Project Structure  pen_up: 90      # Servo angle for pen up

  pen_down: 255   # Servo angle for pen down

```  dwell_time: 0.15 # Settling time (seconds)

ax5-plotter-mcp/

├── simple_plotter_app.py      # Main GUI applicationspeeds:

├── simple_converter.py         # Command-line converter  travel: 3000    # Pen up speed (mm/min)

├── test_simple_app.py         # Test suite  draw: 500       # Drawing speed (mm/min)

├── launch_simple_app.sh       # Linux/macOS launcher  

├── launch_simple_app.bat      # Windows launcheroptimization:

├── requirements-simple.txt    # Python dependencies  merge_tolerance: 0.1    # Line merge distance (mm)

├── config/  simplify_tolerance: 0.05 # Path simplification (mm)

│   ├── settings.yaml          # Your configuration  use_tsp: true           # TSP-based path ordering

│   └── settings.example.yaml  # Example configuration```

├── src/

│   ├── plotter/              # Plotter control## Development

│   │   ├── ax5.py           # AX5 plotter implementation

│   │   ├── grbl.py          # GRBL communication### Running Tests

│   │   └── interface.py     # Plotter interface

│   └── utils/               # Utilities```bash

│       └── svg_converter.py # SVG to G-code conversion# Unit tests

├── logs/                     # Application logspytest tests/unit -v

└── output/                   # Generated G-code files

```# Integration tests (requires hardware)

pytest tests/integration -v --hardware

## Advanced Features

# All tests

### Custom Image Processingpytest tests/ -v

```

Edit the `ImageProcessor` class in `simple_plotter_app.py` to add custom processing methods or adjust existing algorithms.

### Code Quality

### Batch Processing

```bash

Use the command-line tool for multiple images:# Format code

black src/ tests/

```bash

for img in *.jpg; do# Lint

    python simple_converter.py "$img" --method cannyruff check src/ tests/

done

```# Type check

mypy src/

### Integration```



The application can be used alongside other plotter control software. Just ensure only one program connects to the plotter at a time.## Deployment on ZimaBoard



## SafetySee `docs/zimaboard_deployment.md` for complete deployment guide including:

- Systemd service configuration

- Keep plotter workspace clear before starting- Automatic startup on boot

- Monitor first few plots to ensure proper operation- USB device persistence

- Use appropriate paper size for plotter dimensions- Firewall configuration

- Have emergency stop accessible- Monitoring setup



## Support & DocumentationQuick systemd setup:



- Full documentation: [SIMPLE_APP_README.md](SIMPLE_APP_README.md)```bash

- Report issues on GitHub# Copy systemd service files

- Check logs in `logs/` directory for debuggingsudo cp scripts/systemd/*.service /etc/systemd/system/



## License# Edit to match your installation path

sudo nano /etc/systemd/system/ax5-api.service

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# Enable and start services

## Acknowledgmentssudo systemctl enable ax5-api ax5-worker redis

sudo systemctl start ax5-api ax5-worker

- Built for AX5 CoreXY pen plotter```

- Uses GRBL 0.9i firmware with servo support

- Image processing powered by OpenCV## Troubleshooting

- SVG optimization via vpype

### Serial Port Not Found

---```bash

# Find Arduino port

**Made with ❤️ for the AX5 plotting community**ls -l /dev/ttyUSB* /dev/ttyACM*

# Add user to dialout group
sudo usermod -aG dialout $USER

# Reboot to apply
```

### GRBL Alarm States
- **ALARM:1** - Hard limit triggered, run `$X` to unlock
- **ALARM:2** - Soft limit triggered, check position
- **ALARM:3** - Abort during cycle, reset with Ctrl-X

### Job Queue Issues
```bash
# Check Redis status
sudo systemctl status redis-server

# Clear failed jobs
rq info --url redis://localhost:6379

# Retry failed job
python -c "from redis import Redis; from rq import Queue; from rq.job import Job; job = Job.fetch('JOB_ID', Redis()); job.retry()"
```

## Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [GRBL Documentation](https://github.com/gnea/grbl/wiki)
- [vpype Documentation](https://vpype.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Support

- GitHub Issues: Report bugs and feature requests
- Discord: Join the DrawingBots community
- Reddit: r/PlotterArt

---

Built with ❤️ for the AX5 plotter community
