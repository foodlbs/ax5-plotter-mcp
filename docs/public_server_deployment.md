# Public AX5 Plotter Server - Deployment Guide

Complete guide for deploying AX5 plotter as a **public internet-accessible service** with authentication, SSL, and security.

---

## ⚠️ Security Warning

**This setup exposes your plotter to the internet.** Ensure you:
- ✅ Use strong passwords and API keys
- ✅ Enable HTTPS/SSL (required)
- ✅ Configure firewall properly
- ✅ Keep software updated
- ✅ Monitor access logs
- ✅ Set appropriate rate limits

**Physical security:** Anyone with access can control your plotter. Consider:
- Monitoring camera near plotter
- Physical access controls
- Auto-shutdown after hours
- Material usage tracking

---

## Architecture

```
Internet
   │
   ▼
[Domain/DNS] your-plotter.com
   │
   ▼
[SSL/HTTPS Certificate] (Let's Encrypt)
   │
   ▼
[Nginx Reverse Proxy] (with rate limiting)
   │
   ▼
[FastAPI Server] (with JWT auth)
   │
   ├─► [Redis Queue]
   │     │
   │     ▼
   │   [RQ Workers] → [AX5 Plotter]
   │
   └─► [User Database] (SQLite/PostgreSQL)
```

---

## Prerequisites

### 1. Domain Name
You need a domain pointing to your server's public IP:
```bash
# Check your public IP
curl ifconfig.me

# Configure DNS A record:
# Type: A
# Name: plotter (or @)
# Value: YOUR.PUBLIC.IP
# TTL: 3600
```

### 2. Port Forwarding (if behind router)
Configure your router to forward ports:
- **Port 80** → ZimaBoard IP:80 (for Let's Encrypt)
- **Port 443** → ZimaBoard IP:443 (for HTTPS)

### 3. Static IP or Dynamic DNS
- **Static IP**: Configure on ZimaBoard (see main deployment guide)
- **Dynamic DNS**: Use service like DuckDNS, No-IP, or Dynu

---

## Installation

### Step 1: Basic Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3-pip redis-server nginx certbot python3-certbot-nginx

# Clone repository
git clone <your-repo> ~/ax5-plotter-mcp
cd ~/ax5-plotter-mcp

# Install Python packages
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Server

```bash
# Copy configuration
cp config/settings.example.yaml config/settings.yaml
nano config/settings.yaml
```

**Key settings:**
```yaml
plotter:
  port: /dev/ttyUSB0  # Your Arduino port

api:
  host: 127.0.0.1  # IMPORTANT: localhost only (nginx will proxy)
  port: 8000

auth:
  enabled: true
  secret_key: "YOUR_RANDOM_SECRET_HERE"  # Generate: openssl rand -hex 32
  
ssl:
  enabled: true  # Will be handled by nginx
```

### Step 3: SSL Certificate (Let's Encrypt)

```bash
# Get SSL certificate
sudo certbot --nginx -d your-plotter.com

# Certificate auto-renewal test
sudo certbot renew --dry-run
```

### Step 4: Nginx Reverse Proxy

Create nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/ax5-plotter
```

Add configuration:
```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/m;

# Upstream
upstream ax5_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-plotter.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-plotter.com;
    
    # SSL configuration (certbot will manage these)
    ssl_certificate /etc/letsencrypt/live/your-plotter.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-plotter.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Max upload size
    client_max_body_size 20M;
    
    # API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://ax5_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for SSE
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
    
    # Upload endpoint with stricter limit
    location /api/plots/upload {
        limit_req zone=upload_limit burst=5 nodelay;
        
        proxy_pass http://ax5_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        client_max_body_size 20M;
    }
    
    # Health check
    location /health {
        proxy_pass http://ax5_backend;
        access_log off;
    }
    
    # API docs (optional - disable in production)
    location /docs {
        # auth_basic "Restricted";
        # auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://ax5_backend;
        proxy_set_header Host $host;
    }
    
    # Optional: Serve frontend
    location / {
        root /var/www/plotter-frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/ax5-plotter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 5: Systemd Services

```bash
# Copy service files
sudo cp scripts/systemd/*.service /etc/systemd/system/

# Edit paths
sudo nano /etc/systemd/system/ax5-api.service
sudo nano /etc/systemd/system/ax5-worker.service

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable redis-server ax5-api ax5-worker nginx
sudo systemctl start redis-server ax5-api ax5-worker nginx
```

### Step 6: Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt)
sudo ufw allow 443/tcp  # HTTPS

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## User Management

### Create Admin Account

The system creates a default admin account on first run. **Change the password immediately:**

```bash
# Get admin API key from logs
sudo journalctl -u ax5-api | grep "API Key"

# Or reset admin password
source .venv/bin/activate
python scripts/reset_admin.py
```

### Create Users via API

```bash
# Register new user
curl -X POST https://your-plotter.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'

# Response includes API key
{
  "id": 2,
  "username": "john",
  "email": "john@example.com",
  "api_key": "abc123xyz...",
  "jobs_per_hour": 10,
  "jobs_per_day": 50
}
```

### Admin Management

```bash
# Login as admin
curl -X POST https://your-plotter.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-admin-password"
  }'

# Save the access_token from response

# List all users
curl https://your-plotter.com/api/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Update user rate limits
curl -X PATCH https://your-plotter.com/api/auth/users/2 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jobs_per_hour": 20,
    "jobs_per_day": 100
  }'

# Disable user
curl -X PATCH https://your-plotter.com/api/auth/users/2 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## Client Usage

### Authentication Methods

Users can authenticate using either:

**1. JWT Token (recommended for web apps):**
```bash
# Login to get token
curl -X POST https://your-plotter.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "password123"}'

# Use token in requests
curl https://your-plotter.com/api/plotter/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**2. API Key (for scripts/automation):**
```bash
# Use API key directly
curl https://your-plotter.com/api/plotter/status \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Submit Plot Job

```bash
# Upload SVG
curl -X POST https://your-plotter.com/api/plots/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@drawing.svg"

# Submit plot
curl -X POST https://your-plotter.com/api/plots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "svg_file": "uploads/john_abc123.svg",
    "priority": "normal",
    "optimize": true
  }'
```

### Python Client Example

```python
import requests

class PlotterClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def upload_svg(self, filepath):
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/api/plots/upload",
                files=files,
                headers=self.headers
            )
        return response.json()
    
    def submit_plot(self, svg_file, priority="normal"):
        data = {
            "svg_file": svg_file,
            "priority": priority,
            "optimize": True
        }
        response = requests.post(
            f"{self.base_url}/api/plots",
            json=data,
            headers=self.headers
        )
        return response.json()
    
    def get_status(self, job_id):
        response = requests.get(
            f"{self.base_url}/api/plots/{job_id}",
            headers=self.headers
        )
        return response.json()

# Usage
client = PlotterClient("https://your-plotter.com", "your-api-key")

# Upload and plot
upload_result = client.upload_svg("drawing.svg")
job = client.submit_plot(upload_result['file_path'])
print(f"Job submitted: {job['job_id']}")

# Check status
status = client.get_status(job['job_id'])
print(f"Status: {status['status']} - {status['progress']}%")
```

---

## Monitoring & Maintenance

### Check Service Status

```bash
# Service status
sudo systemctl status ax5-api ax5-worker nginx redis

# View logs
sudo journalctl -u ax5-api -f
sudo journalctl -u ax5-worker -f
sudo tail -f /var/log/nginx/access.log
```

### Monitor Usage

```bash
# Active users
curl https://your-plotter.com/api/auth/users \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Queue status
source .venv/bin/activate
rq info --url redis://localhost:6379

# System resources
htop
df -h
```

### Database Backup

```bash
# Backup users database
sudo cp ~/ax5-plotter-mcp/users.db ~/backups/users-$(date +%Y%m%d).db

# Automate with cron
crontab -e
# Add: 0 2 * * * cp ~/ax5-plotter-mcp/users.db ~/backups/users-$(date +\%Y\%m\%d).db
```

### SSL Certificate Renewal

Certbot auto-renews, but verify:
```bash
# Test renewal
sudo certbot renew --dry-run

# Certificate expiry
sudo certbot certificates
```

---

## Security Best Practices

### 1. Strong Authentication
- Enforce strong passwords (min 12 characters)
- Rotate API keys regularly
- Use 2FA for admin accounts (future feature)

### 2. Rate Limiting
- Configure per-user limits in database
- Monitor for abuse in nginx logs
- Implement CAPTCHA for registration (optional)

### 3. Input Validation
- SVG file validation
- File size limits
- Malicious code detection

### 4. Monitoring
```bash
# Install fail2ban for brute force protection
sudo apt install fail2ban

# Configure for nginx
sudo nano /etc/fail2ban/jail.local
```

Add:
```ini
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
```

### 5. Regular Updates
```bash
# Weekly update script
#!/bin/bash
sudo apt update && sudo apt upgrade -y
cd ~/ax5-plotter-mcp
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart ax5-api ax5-worker
```

---

## Troubleshooting

### Can't Connect via Domain

```bash
# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check DNS
dig your-plotter.com
nslookup your-plotter.com

# Check SSL
sudo certbot certificates
```

### Authentication Issues

```bash
# Check user database
source .venv/bin/activate
sqlite3 users.db "SELECT * FROM users;"

# Reset user password
python scripts/reset_password.py username
```

### Rate Limit Errors

```bash
# Check nginx rate limits
sudo tail -f /var/log/nginx/error.log | grep limiting

# Adjust in nginx config
sudo nano /etc/nginx/sites-available/ax5-plotter
```

---

## Scaling

### Multiple Workers

```bash
# Run multiple workers
sudo cp /etc/systemd/system/ax5-worker.service \
      /etc/systemd/system/ax5-worker@.service

# Start multiple instances
sudo systemctl start ax5-worker@{1..3}.service
```

### PostgreSQL (Production)

For high traffic, switch to PostgreSQL:

```yaml
# config/settings.yaml
auth:
  database_url: "postgresql://user:pass@localhost/plotter_db"
```

### CDN for Static Files

Use Cloudflare or similar for:
- DDoS protection
- SSL termination
- Static file caching
- Geographic distribution

---

## Cost Estimates

### ZimaBoard (24/7 operation)
- Power: ~$10-15/year
- Domain: ~$12/year
- Bandwidth: Usually free (residential)

### VPS Alternative
If you don't want to expose home network:
- DigitalOcean Droplet: $6-12/month
- AWS Lightsail: $5-10/month
- Linode: $5-10/month
- **Note:** Physical plotter must still connect (VPN tunnel)

---

## Complete Example

**Full workflow from setup to first remote plot:**

```bash
# 1. Setup domain and SSL
sudo certbot --nginx -d your-plotter.com

# 2. Start services
sudo systemctl start ax5-api ax5-worker

# 3. Create user account
curl -X POST https://your-plotter.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"artist1","email":"artist@example.com","password":"SecurePass123!"}'

# 4. Save API key from response
API_KEY="abc123xyz..."

# 5. Upload SVG
curl -X POST https://your-plotter.com/api/plots/upload \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@myart.svg"

# 6. Submit plot
curl -X POST https://your-plotter.com/api/plots \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"svg_file":"uploads/artist1_xyz.svg"}'

# 7. Watch it plot from anywhere in the world! 🎨
```

---

## Support & Community

- **Issues:** GitHub Issues
- **Discord:** DrawingBots community
- **Reddit:** r/PlotterArt
- **Security Issues:** Email privately (don't post publicly)

---

**Your AX5 plotter is now accessible from anywhere in the world! 🌍🎨🤖**
