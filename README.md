# AX5 Plotter MCP Server (Public Edition)

**Model Context Protocol (MCP) server for intelligent control of AX5 pen plotter with CoreXY kinematics and GRBL 0.9 firmware.**

This project provides a complete plotter control system with:
- 🔐 **Authentication & User Management** - Multi-user support with JWT/API key auth
- 🌐 **Public Internet Access** - Deploy as internet-accessible service with SSL
- 🤖 **MCP Integration** - AI-assisted plotter control via Model Context Protocol
- 🌐 **REST API** - FastAPI-based web interface for job submission and monitoring
- 📊 **Real-time Progress** - Server-Sent Events (SSE) for live job updates
- 🔄 **Job Queue** - Redis Queue (RQ) for reliable job processing
- 📐 **SVG Conversion** - Optimized G-code generation with path optimization
- 🎯 **CoreXY Support** - Native support for AX5 CoreXY kinematics
- 🖊️ **Servo Control** - Pen up/down via modified GRBL firmware
- ⚡ **Rate Limiting** - Prevent abuse with per-user quotas
- 👥 **Admin Panel** - Manage users and monitor usage

## Hardware Requirements

- **AX5 Pen Plotter** with CoreXY kinematics
- **Arduino UNO** running GRBL 0.9i with servo support
- **ZimaBoard 832** or similar Linux SBC (specs below)
- USB connection from server to Arduino

### ZimaBoard 832 Compatibility ✅

This server is fully compatible with ZimaBoard 832:
- **CPU**: Intel Celeron N3450 (quad-core x86) - ✅ Sufficient
- **RAM**: 8GB - ✅ More than adequate (2GB minimum)
- **Storage**: 32GB eMMC - ✅ Plenty for OS + server + job storage
- **USB**: Multiple USB 3.0 ports - ✅ For Arduino connection
- **OS**: Ubuntu/Debian Linux - ✅ Fully supported

## Quick Start

### Local Deployment (Single User)

```bash
# On ZimaBoard or any Linux system
sudo apt update
sudo apt install -y python3.11 python3-pip redis-server

# Install uv (recommended) or pip
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Public Deployment (Multi-User, Internet-Accessible)

**⚠️ For internet-accessible deployment with authentication:**

See **[Public Server Deployment Guide](docs/public_server_deployment.md)** for complete instructions including:
- SSL/HTTPS setup with Let's Encrypt
- Nginx reverse proxy configuration
- User authentication system
- Rate limiting and security
- Domain configuration

**Quick summary:**
```bash
# 1. Setup domain and SSL
sudo certbot --nginx -d your-plotter.com

# 2. Configure authentication
cp config/settings.example.yaml config/settings.yaml
nano config/settings.yaml  # Set auth.enabled=true

# 3. Start services
sudo systemctl enable ax5-api ax5-worker nginx
sudo systemctl start ax5-api ax5-worker nginx

# 4. Access at https://your-plotter.com
```

### 2. Configure GRBL Firmware

Flash your Arduino with GRBL 0.9i servo-enabled firmware:
- Recommended: [arnabdasbwn/grbl-coreXY-servo](https://github.com/arnabdasbwn/grbl-coreXY-servo)
- Alternative: [cojarbi/grbl-servo-CoreXY](https://github.com/cojarbi/grbl-servo-CoreXY)

### 3. Configure Settings

```bash
# Copy example configuration
cp config/settings.example.yaml config/settings.yaml

# Edit with your serial port
nano config/settings.yaml
```

### 4. Start Services

```bash
# Start Redis
sudo systemctl start redis-server

# Start API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Start RQ worker (in another terminal)
python src/workers/plot_worker.py

# Or use systemd services (see docs/deployment.md)
```

### 5. Test MCP Server

```bash
# Install in Claude Desktop
uv run mcp install src/mcp_server/ax5_mcp.py --name "AX5 Plotter"

# Or test with MCP Inspector
uv run mcp dev src/mcp_server/ax5_mcp.py
```

## Project Structure

```
ax5-plotter-mcp/
├── src/
│   ├── mcp_server/         # MCP server implementation
│   │   ├── ax5_mcp.py      # Main MCP server
│   │   └── tools.py        # MCP tool definitions
│   ├── api/                # FastAPI REST API
│   │   ├── main.py         # API server
│   │   └── routes/         # API endpoints
│   ├── plotter/            # Hardware abstraction
│   │   ├── interface.py    # Abstract plotter interface
│   │   ├── ax5.py          # AX5 implementation
│   │   └── grbl.py         # GRBL communication
│   ├── workers/            # Background job workers
│   │   └── plot_worker.py  # RQ worker for plot jobs
│   └── utils/              # Utilities
│       ├── svg_converter.py
│       ├── gcode_generator.py
│       └── path_optimizer.py
├── config/                 # Configuration files
│   ├── settings.yaml
│   └── grbl_profiles/
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Deployment scripts
└── uploads/                # SVG file uploads
```

## API Endpoints

### Authentication (Public Server)

When `auth.enabled=true` in config:

**Register:**
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/change-password` - Change password
- `POST /api/auth/regenerate-api-key` - Get new API key

**Admin:**
- `GET /api/auth/users` - List all users (admin only)
- `PATCH /api/auth/users/{id}` - Modify user (admin only)
- `DELETE /api/auth/users/{id}` - Delete user (admin only)

### Plot Management
- `POST /api/plots` - Submit plot job (requires auth if enabled)
- `POST /api/plots/upload` - Upload SVG file (requires auth if enabled)
- `GET /api/plots/{id}` - Get job status
- `GET /api/plots/{id}/stream` - SSE progress stream
- `DELETE /api/plots/{id}` - Cancel job
- `GET /api/plots` - List all jobs

### Plotter Control
- `POST /api/plotter/home` - Home plotter
- `GET /api/plotter/status` - Get current status
- `POST /api/plotter/pen` - Manual pen control

## MCP Tools

When using Claude Desktop or other MCP clients:

- `get_plotter_status()` - Check plotter state and position
- `submit_plot_job(svg_file, priority)` - Queue SVG for plotting
- `cancel_job(job_id)` - Stop running job
- `home_plotter()` - Execute homing cycle
- `list_jobs(status)` - View job queue

## Configuration

Edit `config/settings.yaml`:

```yaml
plotter:
  port: /dev/ttyUSB0  # Serial port for Arduino
  baud: 115200
  dimensions:
    width: 210   # A5 width (mm)
    height: 150  # A5 height (mm)
  
servo:
  pen_up: 90      # Servo angle for pen up
  pen_down: 255   # Servo angle for pen down
  dwell_time: 0.15 # Settling time (seconds)

speeds:
  travel: 3000    # Pen up speed (mm/min)
  draw: 500       # Drawing speed (mm/min)
  
optimization:
  merge_tolerance: 0.1    # Line merge distance (mm)
  simplify_tolerance: 0.05 # Path simplification (mm)
  use_tsp: true           # TSP-based path ordering
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires hardware)
pytest tests/integration -v --hardware

# All tests
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Deployment on ZimaBoard

See `docs/zimaboard_deployment.md` for complete deployment guide including:
- Systemd service configuration
- Automatic startup on boot
- USB device persistence
- Firewall configuration
- Monitoring setup

Quick systemd setup:

```bash
# Copy systemd service files
sudo cp scripts/systemd/*.service /etc/systemd/system/

# Edit to match your installation path
sudo nano /etc/systemd/system/ax5-api.service

# Enable and start services
sudo systemctl enable ax5-api ax5-worker redis
sudo systemctl start ax5-api ax5-worker
```

## Troubleshooting

### Serial Port Not Found
```bash
# Find Arduino port
ls -l /dev/ttyUSB* /dev/ttyACM*

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
