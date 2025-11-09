# ZimaBoard 832 Deployment Guide

Complete guide for deploying the AX5 Plotter MCP Server on ZimaBoard 832.

## ZimaBoard 832 Specifications

✅ **Fully Compatible with AX5 Plotter Server**

- **CPU**: Intel Celeron N3450 (quad-core, 1.1-2.2GHz)
- **RAM**: 8GB DDR3L
- **Storage**: 32GB eMMC
- **USB**: 2x USB 3.0, 2x USB 2.0
- **Network**: 2x Gigabit Ethernet
- **OS**: Ubuntu/Debian Linux

The ZimaBoard 832 is more than capable of running:
- FastAPI server
- Redis database
- RQ workers
- Serial communication to Arduino
- Path optimization algorithms
- MCP server

**Performance Notes:**
- Can handle multiple concurrent plot jobs
- Real-time G-code streaming without stuttering
- Sufficient RAM for large SVG processing
- Low power consumption (~6W typical)

## Initial Setup

### 1. OS Installation

Install Ubuntu 22.04 LTS (recommended):

```bash
# Download Ubuntu Server 22.04 LTS
# Flash to USB drive with Rufus/Etcher
# Boot ZimaBoard and install

# After installation, update system
sudo apt update
sudo apt upgrade -y
```

### 2. Install Dependencies

```bash
# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Redis
sudo apt install -y redis-server

# Install git
sudo apt install -y git

# Install system dependencies
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# Optional: Install vpype for optimization
pipx install "vpype[all]"
pipx inject vpype vpype-gcode
```

### 3. User and Permissions

```bash
# Add user to dialout group for serial port access
sudo usermod -aG dialout $USER

# Create directories
mkdir -p ~/ax5-plotter-mcp
cd ~/ax5-plotter-mcp
```

### 4. Clone Repository

```bash
# Clone your repository
git clone <your-repo-url> ~/ax5-plotter-mcp
cd ~/ax5-plotter-mcp

# Or initialize from scratch
git init
# ... add files
```

### 5. Python Environment

```bash
# Install uv (fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### 6. Configure Settings

```bash
# Copy example configuration
cp config/settings.example.yaml config/settings.yaml

# Edit configuration
nano config/settings.yaml
```

**Key settings to configure:**

```yaml
plotter:
  port: /dev/ttyUSB0  # Check with: ls -l /dev/ttyUSB*
  
api:
  host: 0.0.0.0  # Listen on all interfaces
  port: 8000
  cors_origins:
    - http://192.168.1.100:3000  # Your computer's IP
```

### 7. USB Device Persistence

Create udev rule for consistent serial port naming:

```bash
# Find Arduino device info
udevadm info -a -n /dev/ttyUSB0 | grep -E 'ATTRS{idVendor}|ATTRS{idProduct}'

# Create udev rule
sudo nano /etc/udev/rules.d/99-ax5-plotter.rules
```

Add rule (adjust vendor/product IDs):
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ax5plotter"
```

Then:
```bash
# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Now use /dev/ax5plotter in your config
```

## Service Installation

### 1. Install Systemd Services

```bash
# Copy service files
sudo cp scripts/systemd/ax5-api.service /etc/systemd/system/
sudo cp scripts/systemd/ax5-worker.service /etc/systemd/system/

# Edit to match your installation path
sudo nano /etc/systemd/system/ax5-api.service
# Change User, Group, and WorkingDirectory

sudo nano /etc/systemd/system/ax5-worker.service
# Same changes
```

### 2. Enable Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable redis-server
sudo systemctl enable ax5-api
sudo systemctl enable ax5-worker

# Start services
sudo systemctl start redis-server
sudo systemctl start ax5-api
sudo systemctl start ax5-worker
```

### 3. Check Status

```bash
# Check all services
sudo systemctl status redis-server
sudo systemctl status ax5-api
sudo systemctl status ax5-worker

# View logs
sudo journalctl -u ax5-api -f
sudo journalctl -u ax5-worker -f
```

## Network Configuration

### Firewall Setup

```bash
# Install UFW
sudo apt install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow API access
sudo ufw allow 8000/tcp

# Allow MCP (if using HTTP transport)
sudo ufw allow 8001/tcp

# Enable firewall
sudo ufw enable
```

### Static IP (Optional)

Edit netplan configuration:

```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply:
```bash
sudo netplan apply
```

## Testing

### 1. Test Serial Connection

```bash
# Activate environment
source .venv/bin/activate

# Test Python serial
python -c "import serial; print(serial.Serial('/dev/ttyUSB0', 115200))"
```

### 2. Test API

```bash
# Check health endpoint
curl http://localhost:8000/health

# Get plotter status
curl http://localhost:8000/api/plotter/status
```

### 3. Test MCP Server

```bash
# Run MCP inspector
uv run mcp dev src/mcp_server/ax5_mcp.py
```

### 4. Submit Test Job

```bash
# Upload SVG
curl -X POST -F "file=@test.svg" http://localhost:8000/api/plots/upload

# Submit plot
curl -X POST http://localhost:8000/api/plots \
  -H "Content-Type: application/json" \
  -d '{"svg_file": "uploads/test.svg", "priority": "normal"}'
```

## Monitoring

### System Resources

```bash
# Monitor CPU and memory
htop

# Monitor disk usage
df -h

# Monitor temperatures
sensors  # Install with: sudo apt install lm-sensors
```

### Service Logs

```bash
# Follow API logs
sudo journalctl -u ax5-api -f

# Follow worker logs
sudo journalctl -u ax5-worker -f

# Filter by time
sudo journalctl -u ax5-api --since "1 hour ago"
```

### Redis Queue

```bash
# Check queue status
source .venv/bin/activate
rq info --url redis://localhost:6379

# Monitor jobs
watch -n 1 'rq info --url redis://localhost:6379'
```

## Automatic Startup

### Create Startup Script

```bash
nano ~/startup-check.sh
```

```bash
#!/bin/bash
# Startup check script for AX5 plotter

echo "Checking AX5 Plotter services..."

# Check serial port
if [ -e /dev/ttyUSB0 ]; then
    echo "✓ Serial port found: /dev/ttyUSB0"
else
    echo "✗ Serial port not found"
fi

# Check services
for service in redis-server ax5-api ax5-worker; do
    if systemctl is-active --quiet $service; then
        echo "✓ $service is running"
    else
        echo "✗ $service is not running"
        systemctl start $service
    fi
done

echo "Setup complete!"
```

Make executable:
```bash
chmod +x ~/startup-check.sh

# Add to crontab
crontab -e
# Add line:
@reboot /home/zimaboard/startup-check.sh >> /home/zimaboard/startup.log 2>&1
```

## Remote Access

### Access from Another Computer

1. Find ZimaBoard IP:
```bash
hostname -I
```

2. Access API from your computer:
```
http://192.168.1.100:8000
```

3. Configure Claude Desktop to use remote MCP server:

In Claude Desktop's MCP config:
```json
{
  "mcpServers": {
    "ax5-plotter": {
      "url": "http://192.168.1.100:8001"
    }
  }
}
```

### SSH Access

```bash
# From your computer
ssh zimaboard@192.168.1.100

# Set up key-based auth (recommended)
ssh-copy-id zimaboard@192.168.1.100
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar czf ~/backups/ax5-backup-$DATE.tar.gz \
    ~/ax5-plotter-mcp/config/ \
    ~/ax5-plotter-mcp/uploads/ \
    ~/ax5-plotter-mcp/output/

# Keep only last 7 backups
ls -t ~/backups/ax5-backup-*.tar.gz | tail -n +8 | xargs rm -f
```

### Recovery

```bash
# Restore from backup
tar xzf ~/backups/ax5-backup-YYYYMMDD.tar.gz -C ~/
```

## Performance Tuning

### Redis Optimization

Edit `/etc/redis/redis.conf`:
```
maxmemory 1gb
maxmemory-policy allkeys-lru
```

Restart Redis:
```bash
sudo systemctl restart redis-server
```

### System Optimization

```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Update CPU governor for performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed status
sudo systemctl status ax5-api -l

# Check for port conflicts
sudo netstat -tulpn | grep 8000

# Test manually
cd ~/ax5-plotter-mcp
source .venv/bin/activate
python src/api/main.py
```

### Serial Port Issues

```bash
# Check permissions
ls -l /dev/ttyUSB0

# Test communication
screen /dev/ttyUSB0 115200
# Press Ctrl-A then K to exit

# Check for conflicts
sudo lsof /dev/ttyUSB0
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Restart services
sudo systemctl restart ax5-api ax5-worker
```

## Security

### Basic Hardening

```bash
# Update regularly
sudo apt update && sudo apt upgrade

# Install fail2ban
sudo apt install fail2ban

# Configure firewall (UFW)
# ... (see Network Configuration above)

# Disable root SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd
```

### API Security (Production)

Add authentication to API:
- Use API keys
- Enable HTTPS with Let's Encrypt
- Implement rate limiting

## Conclusion

Your ZimaBoard 832 is now configured as a dedicated AX5 plotter server with:
- ✅ Automatic startup on boot
- ✅ Remote API access
- ✅ MCP integration for AI control
- ✅ Job queue management
- ✅ Monitoring and logging

**Next steps:**
1. Test with real plots
2. Configure Claude Desktop for remote access
3. Set up automatic backups
4. Monitor performance over time

For support, check:
- System logs: `journalctl -xe`
- Application logs: `sudo journalctl -u ax5-api`
- Redis queue: `rq info`
