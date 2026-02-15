# PebbleMind Production Deployment Guide

Complete guide for deploying PebbleMind in production environments with enterprise-grade security and performance.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [SSL/HTTPS Setup](#sslhttps-setup)
4. [Reverse Proxy Configuration](#reverse-proxy-configuration)
5. [Systemd Service](#systemd-service)
6. [Docker Deployment](#docker-deployment)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Security Hardening](#security-hardening)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB
- OS: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)

**Recommended:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 20GB+ SSD
- OS: Ubuntu 22.04 LTS

**For Edge Devices:**
- MacBook Air M1/M2: Optimized
- Raspberry Pi 4 (8GB): Supported
- Intel NUC: Excellent performance

### Software Dependencies

```bash
# Python 3.9+
python3 --version

# Git
git --version

# Optional: Docker
docker --version
```

---

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/pebblemind.git
cd pebblemind

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Generate secure API key
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))" >> .env

# Generate session secret
python3 -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(32))" >> .env

# Edit configuration
nano .env
```

**Critical Settings for Production:**

```bash
# General
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0  # Listen on all interfaces
API_PORT=8000
API_KEY=<your-generated-key>
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# HTTPS (see SSL setup section)
ENABLE_HTTPS=true
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# Security
RATE_LIMIT_PER_MINUTE=60
ENABLE_SECURITY_HEADERS=true

# Performance
THREADS=4  # Adjust based on CPU cores
CONTEXT_LENGTH=2048
MAX_TOKENS=256
```

### 3. Test Configuration

```bash
# Run tests
pytest tests/ -v

# Run security tests
pytest tests/test_security.py -v

# Run E2E tests
pytest tests/test_e2e.py -v
```

### 4. Start Server

```bash
# Development
python -m pebblemind.cli

# Production (with gunicorn)
gunicorn pebblemind.api.server:app \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-logfile /var/log/pebblemind/access.log \
  --error-logfile /var/log/pebblemind/error.log
```

---

## SSL/HTTPS Setup

### Option 1: Let's Encrypt (Recommended)

**Install Certbot:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot

# RHEL/CentOS
sudo yum install certbot
```

**Obtain Certificate:**

```bash
# For standalone authentication (port 80 must be free)
sudo certbot certonly --standalone -d yourdomain.com

# For webroot authentication (if you have a web server)
sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com
```

**Configure PebbleMind:**

```bash
# In .env
ENABLE_HTTPS=true
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**Auto-Renewal:**

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab (runs twice daily)
sudo crontab -e
# Add line:
0 0,12 * * * certbot renew --quiet --post-hook "systemctl restart pebblemind"
```

### Option 2: Self-Signed Certificate (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout privkey.pem \
  -out fullchain.pem \
  -days 365 \
  -subj "/CN=localhost"

# Move to secure location
sudo mkdir -p /etc/pebblemind/certs
sudo mv *.pem /etc/pebblemind/certs/
sudo chmod 600 /etc/pebblemind/certs/*.pem

# Configure
ENABLE_HTTPS=true
SSL_CERT_PATH=/etc/pebblemind/certs/fullchain.pem
SSL_KEY_PATH=/etc/pebblemind/certs/privkey.pem
```

⚠️ **Self-signed certificates will show browser warnings. Use Let's Encrypt for production.**

---

## Reverse Proxy Configuration

### Nginx (Recommended)

**Install Nginx:**

```bash
sudo apt update
sudo apt install nginx
```

**Configuration:**

```nginx
# /etc/nginx/sites-available/pebblemind

upstream pebblemind {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers (additional layer)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Logging
    access_log /var/log/nginx/pebblemind-access.log combined;
    error_log /var/log/nginx/pebblemind-error.log warn;

    # File upload limit
    client_max_body_size 25M;

    # Proxy Configuration
    location / {
        proxy_pass http://pebblemind;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint (bypass rate limiting)
    location /health {
        proxy_pass http://pebblemind;
        access_log off;
    }
}
```

**Enable and Test:**

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/pebblemind /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable auto-start
sudo systemctl enable nginx
```

### Apache Alternative

```apache
# /etc/apache2/sites-available/pebblemind.conf

<VirtualHost *:80>
    ServerName yourdomain.com
    Redirect permanent / https://yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/yourdomain.com/privkey.pem

    # Proxy Configuration
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # WebSocket support
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:8000/$1" [P,L]

    # Security Headers
    Header always set Strict-Transport-Security "max-age=31536000"
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
</VirtualHost>
```

---

## Systemd Service

### Create Service File

```bash
sudo nano /etc/systemd/system/pebblemind.service
```

```ini
[Unit]
Description=PebbleMind AI Server
After=network.target

[Service]
Type=simple
User=pebblemind
Group=pebblemind
WorkingDirectory=/opt/pebblemind
Environment="PATH=/opt/pebblemind/venv/bin"
EnvironmentFile=/opt/pebblemind/.env
ExecStart=/opt/pebblemind/venv/bin/python -m pebblemind.api.server

# Restart configuration
Restart=always
RestartSec=10
StartLimitInterval=0

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/pebblemind/data /var/log/pebblemind

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pebblemind

[Install]
WantedBy=multi-user.target
```

### Create Dedicated User

```bash
# Create user
sudo useradd -r -s /bin/false pebblemind

# Create directories
sudo mkdir -p /opt/pebblemind
sudo mkdir -p /var/log/pebblemind

# Set ownership
sudo chown -R pebblemind:pebblemind /opt/pebblemind
sudo chown -R pebblemind:pebblemind /var/log/pebblemind

# Set permissions
sudo chmod 750 /opt/pebblemind
sudo chmod 750 /var/log/pebblemind
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable pebblemind

# Start service
sudo systemctl start pebblemind

# Check status
sudo systemctl status pebblemind

# View logs
sudo journalctl -u pebblemind -f
```

---

## Docker Deployment

### Dockerfile

Already provided in the repository. Build and run:

```bash
# Build image
docker build -t pebblemind:latest .

# Run container
docker run -d \
  --name pebblemind \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  pebblemind:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  pebblemind:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - pebblemind
    restart: unless-stopped
```

---

## Performance Tuning

### System Optimization

```bash
# Increase file descriptors
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize TCP
sudo sysctl -w net.core.somaxconn=4096
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=4096

# Make persistent
echo "net.core.somaxconn=4096" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog=4096" | sudo tee -a /etc/sysctl.conf
```

### Application Tuning

```bash
# In .env

# Threading (set to number of CPU cores)
THREADS=4

# Context length (reduce for faster inference)
CONTEXT_LENGTH=1024

# Batch size (increase for throughput, decrease for latency)
BATCH_SIZE=512

# Enable optimizations
ENABLE_BLAS=true
ENABLE_NATIVE=true
```

### Database Optimization

```sql
-- For SQLite databases

-- Enable WAL mode (better concurrency)
PRAGMA journal_mode=WAL;

-- Increase cache size (in KB)
PRAGMA cache_size=-64000;  -- 64MB

-- Optimize for performance
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
```

---

## Monitoring & Logging

### Prometheus Metrics

Install Prometheus client:

```bash
pip install prometheus-client
```

Add to application:

```python
from prometheus_client import start_http_server, Counter, Histogram

# Start metrics server
start_http_server(9090)
```

### Log Rotation

```bash
# /etc/logrotate.d/pebblemind

/var/log/pebblemind/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pebblemind pebblemind
    sharedscripts
    postrotate
        systemctl reload pebblemind > /dev/null 2>&1 || true
    endscript
}
```

### Health Monitoring

```bash
# Simple health check script
#!/bin/bash
# /usr/local/bin/pebblemind-health.sh

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✓ PebbleMind is healthy"
    exit 0
else
    echo "✗ PebbleMind is unhealthy (HTTP $RESPONSE)"
    # Send alert
    exit 1
fi
```

Add to cron:

```bash
*/5 * * * * /usr/local/bin/pebblemind-health.sh || mail -s "PebbleMind Health Alert" admin@example.com
```

---

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# /usr/local/bin/pebblemind-backup.sh

BACKUP_DIR="/backup/pebblemind"
DATA_DIR="/opt/pebblemind/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup databases
tar -czf $BACKUP_DIR/pebblemind_$TIMESTAMP.tar.gz $DATA_DIR

# Keep only last 7 days
find $BACKUP_DIR -name "pebblemind_*.tar.gz" -mtime +7 -delete

# Log
echo "[$TIMESTAMP] Backup completed" >> /var/log/pebblemind-backup.log
```

Schedule:

```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/pebblemind-backup.sh
```

### Recovery

```bash
# Stop service
sudo systemctl stop pebblemind

# Restore from backup
tar -xzf /backup/pebblemind/pebblemind_TIMESTAMP.tar.gz -C /opt/pebblemind/

# Fix permissions
sudo chown -R pebblemind:pebblemind /opt/pebblemind/data

# Start service
sudo systemctl start pebblemind
```

---

## Security Hardening

### Firewall Configuration

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Fail2Ban

```bash
# Install
sudo apt install fail2ban

# Configure
sudo nano /etc/fail2ban/jail.local
```

```ini
[pebblemind-auth]
enabled = true
port = http,https
filter = pebblemind-auth
logpath = /var/log/pebblemind/access.log
maxretry = 5
bantime = 3600
```

### Security Auditing

```bash
# Run security audit
sudo lynis audit system

# Check SSL configuration
nmap --script ssl-enum-ciphers -p 443 yourdomain.com

# Test security headers
curl -I https://yourdomain.com | grep -E "Strict-Transport|X-Frame|X-Content|X-XSS"
```

---

## Troubleshooting

### Common Issues

**1. Service won't start**

```bash
# Check logs
sudo journalctl -u pebblemind -n 50

# Check configuration
python -m pebblemind.cli --check-config

# Test manually
sudo -u pebblemind python -m pebblemind.api.server
```

**2. SSL errors**

```bash
# Verify certificate
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -noout -text

# Check permissions
ls -la /etc/letsencrypt/live/yourdomain.com/

# Test SSL
openssl s_client -connect yourdomain.com:443
```

**3. Performance issues**

```bash
# Check resource usage
htop

# Check database size
du -sh /opt/pebblemind/data/*.db

# Optimize databases
python -m pebblemind.cli --optimize-db

# Check for memory leaks
sudo systemctl status pebblemind
```

**4. Authentication failures**

```bash
# Verify API key
grep API_KEY /opt/pebblemind/.env

# Test authentication
curl -H "Authorization: Bearer YOUR_KEY" https://yourdomain.com/v1/models
```

### Getting Help

- **Documentation**: See README.md, SECURITY.md
- **Issues**: GitHub Issues
- **Community**: Discord/Slack (if available)
- **Email**: support@example.com

---

## Checklist: Production Deployment

- [ ] Generate secure API keys and secrets
- [ ] Configure .env file for production
- [ ] Obtain and install SSL certificates
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Create systemd service
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Enable monitoring and health checks
- [ ] Test all security features
- [ ] Run performance benchmarks
- [ ] Document custom configuration
- [ ] Set up alerting for critical failures
- [ ] Create disaster recovery plan
- [ ] Train team on operations

---

**Last Updated:** February 15, 2026
**Version:** 1.0.0
**Status:** Production Ready ✅
