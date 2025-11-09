# Quick Start Guide

Get your AX5 plotter MCP server running in 5 minutes.

## Prerequisites

- AX5 pen plotter with Arduino + GRBL 0.9
- Linux system (Ubuntu/Debian preferred)
- USB connection to Arduino
- Python 3.11+

## Installation

### 1. Clone and Install

```bash
git clone <your-repo-url> ax5-plotter-mcp
cd ax5-plotter-mcp
./scripts/install.sh
```

### 2. Configure

```bash
# Edit configuration
nano config/settings.yaml

# Key settings:
# - plotter.port: /dev/ttyUSB0 (check with: ls -l /dev/ttyUSB*)
# - plotter.dimensions: 210x150 (A5 size)
```

### 3. Test Connection

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
python tests/test_basic.py
```

### 4. Start Services

**Terminal 1 - API Server:**
```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Worker:**
```bash
source .venv/bin/activate
python src/workers/plot_worker.py
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get plotter status
curl http://localhost:8000/api/plotter/status
```

## Your First Plot

### Upload SVG

```bash
curl -X POST -F "file=@drawing.svg" http://localhost:8000/api/plots/upload
```

Response:
```json
{
  "file_path": "uploads/abc-123.svg",
  "file_id": "abc-123"
}
```

### Submit Plot Job

```bash
curl -X POST http://localhost:8000/api/plots \
  -H "Content-Type: application/json" \
  -d '{
    "svg_file": "uploads/abc-123.svg",
    "priority": "normal",
    "pen_type": "ballpoint",
    "optimize": true
  }'
```

Response:
```json
{
  "job_id": "def-456",
  "status": "queued",
  "queue_position": 1
}
```

### Monitor Progress

```bash
# Poll for status
curl http://localhost:8000/api/plots/def-456

# Or stream real-time updates (in browser or EventSource)
http://localhost:8000/api/plots/def-456/stream
```

## Using MCP with Claude Desktop

### 1. Install in Claude Desktop

```bash
source .venv/bin/activate
uv run mcp install src/mcp_server/ax5_mcp.py --name "AX5 Plotter"
```

### 2. Use in Claude Desktop

Chat with Claude:
- "Check the plotter status"
- "Plot this SVG file: /path/to/drawing.svg"
- "Show me all current jobs"
- "Home the plotter"

## Next Steps

### Production Deployment (ZimaBoard)

See detailed guide: [docs/zimaboard_deployment.md](docs/zimaboard_deployment.md)

Quick setup:
```bash
# Copy systemd services
sudo cp scripts/systemd/*.service /etc/systemd/system/

# Edit paths in service files
sudo nano /etc/systemd/system/ax5-api.service
sudo nano /etc/systemd/system/ax5-worker.service

# Enable and start
sudo systemctl enable ax5-api ax5-worker redis
sudo systemctl start ax5-api ax5-worker
```

### Web Interface

The API is ready for a web frontend. Example using JavaScript:

```javascript
// Upload SVG
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const upload = await fetch('http://localhost:8000/api/plots/upload', {
  method: 'POST',
  body: formData
});

const { file_path } = await upload.json();

// Submit plot
const plot = await fetch('http://localhost:8000/api/plots', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    svg_file: file_path,
    priority: 'normal',
    optimize: true
  })
});

const { job_id } = await plot.json();

// Stream progress
const eventSource = new EventSource(
  `http://localhost:8000/api/plots/${job_id}/stream`
);

eventSource.addEventListener('progress', (e) => {
  const { progress, status } = JSON.parse(e.data);
  console.log(`${status}: ${progress}%`);
});
```

## Troubleshooting

### Serial Port Not Found

```bash
# List USB devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Check permissions
groups $USER  # Should include 'dialout'

# If not, add and reboot
sudo usermod -aG dialout $USER
```

### Connection Timeout

```bash
# Test serial communication
screen /dev/ttyUSB0 115200
# Press Ctrl-A then K to exit

# Check if another process is using the port
sudo lsof /dev/ttyUSB0
```

### Redis Not Running

```bash
# Check status
sudo systemctl status redis-server

# Start if needed
sudo systemctl start redis-server

# Check connection
redis-cli ping  # Should return "PONG"
```

### Worker Not Processing Jobs

```bash
# Check worker logs
sudo journalctl -u ax5-worker -f

# Or if running manually
python src/workers/plot_worker.py  # Look for errors

# Check Redis queue
source .venv/bin/activate
rq info --url redis://localhost:6379
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/plotter/status` | Get plotter status |
| POST | `/api/plotter/home` | Home plotter |
| POST | `/api/plots/upload` | Upload SVG file |
| POST | `/api/plots` | Submit plot job |
| GET | `/api/plots/{id}` | Get job status |
| GET | `/api/plots/{id}/stream` | Stream progress (SSE) |
| DELETE | `/api/plots/{id}` | Cancel job |
| GET | `/api/plots` | List jobs |

### MCP Tools

- `get_plotter_status()` - Check plotter state
- `submit_plot_job(svg_file, ...)` - Queue plot
- `get_job_status(job_id)` - Check job progress
- `cancel_job(job_id)` - Cancel job
- `home_plotter()` - Execute homing
- `list_jobs(status, limit)` - View queue
- `move_to_position(x, y)` - Manual positioning
- `control_pen(down)` - Manual pen control

## Resources

- Full documentation: [README.md](README.md)
- ZimaBoard deployment: [docs/zimaboard_deployment.md](docs/zimaboard_deployment.md)
- MCP Protocol: https://modelcontextprotocol.io
- GRBL Documentation: https://github.com/gnea/grbl/wiki

## Support

- Issues: GitHub Issues
- Community: r/PlotterArt on Reddit
- Discord: DrawingBots server

---

**Happy plotting! 🎨**
