# Security Guide for PebbleMind

This document outlines the security features, best practices, and guidelines for using PebbleMind securely.

## Table of Contents

1. [Security Features](#security-features)
2. [Secure Configuration](#secure-configuration)
3. [API Security](#api-security)
4. [Data Protection](#data-protection)
5. [Best Practices](#best-practices)
6. [Security Updates](#security-updates)
7. [Reporting Security Issues](#reporting-security-issues)

---

## Security Features

### Implemented Security Controls

#### 1. Authentication & Authorization
- **API Key Authentication**: Bearer token authentication for API endpoints
- **Optional Authentication**: Can be disabled for local development (not recommended for production)
- **Secure Headers**: HTTPBearer security scheme

#### 2. Rate Limiting
- **Per-Client Rate Limiting**: 60 requests per minute per client IP (configurable)
- **429 Status Codes**: Proper HTTP status codes with Retry-After headers
- **In-Memory Tracking**: Lightweight rate limiting for edge devices

#### 3. Input Validation
- **Pydantic Models**: All API inputs validated using Pydantic
- **File Type Validation**: Audio file uploads restricted to safe formats
- **File Size Limits**: Maximum 25MB upload size
- **Content Type Checking**: Validates MIME types for uploads

#### 4. SQL Injection Prevention
- **Parameterized Queries**: All database queries use parameterized statements
- **No String Interpolation**: Eliminated SQL string formatting vulnerabilities
- **Safe Tag Filtering**: Tag searches use proper parameter binding

#### 5. Error Handling
- **Generic Error Messages**: Internal errors don't expose system details
- **Structured Logging**: Detailed errors logged server-side only
- **Exception Context**: Full stack traces in logs, not responses

#### 6. CORS Configuration
- **Configurable Origins**: Control which domains can access the API
- **Credential Support**: Secure cross-origin authentication
- **Method Restrictions**: Limit allowed HTTP methods

---

## Secure Configuration

### Environment Variables

**NEVER commit sensitive values to version control.**

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Generate secure secrets:
   ```bash
   # Generate API key
   python -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"

   # Generate session secret
   python -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(32))"
   ```

3. Set secure permissions on .env file:
   ```bash
   chmod 600 .env
   ```

### Production Configuration Checklist

- [ ] Set strong `API_KEY` (minimum 32 characters)
- [ ] Set strong `SESSION_SECRET` (minimum 32 characters)
- [ ] Disable `DEBUG` mode
- [ ] Set specific `CORS_ORIGINS` (not "*")
- [ ] Enable `ENABLE_HTTPS` with valid SSL certificates
- [ ] Set appropriate `RATE_LIMIT_PER_MINUTE`
- [ ] Review `MAX_UPLOAD_SIZE_MB` for your use case
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`
- [ ] Configure proper `API_HOST` (not 0.0.0.0 for public internet)
- [ ] Enable `ENABLE_ERROR_TRACKING` for monitoring

---

## API Security

### Authentication

#### Using API Keys

All protected endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/v1/chat/completions
```

#### Disabling Authentication (Development Only)

To disable authentication (NOT recommended for production):

```bash
# In .env
API_KEY=
```

### Protected Endpoints

The following endpoints require authentication when `API_KEY` is set:

- `POST /v1/chat/completions` - Chat completions
- `POST /v1/audio/transcriptions` - Speech-to-text
- `POST /v1/audio/speech` - Text-to-speech

### Rate Limiting

Default: 60 requests per minute per client IP

When rate limit is exceeded:
- **Status Code**: 429 Too Many Requests
- **Header**: `Retry-After` (seconds until reset)
- **Response**: JSON error with retry guidance

```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

To adjust rate limit:
```bash
# In .env
RATE_LIMIT_PER_MINUTE=100
```

---

## Data Protection

### Database Security

#### SQLite Security Best Practices

1. **File Permissions**:
   ```bash
   chmod 600 data/longterm_memory.db
   chmod 600 data/vectors.db
   ```

2. **Backup Encryption**:
   ```bash
   # Encrypt backups before storing
   gpg -c data/longterm_memory.db
   ```

3. **Connection Safety**:
   - All queries use parameterized statements
   - No dynamic SQL construction with user input
   - Connection pooling with proper cleanup

### Sensitive Data Handling

#### What PebbleMind Stores

- **Conversation History**: User messages and AI responses
- **Memory Entries**: Long-term memory data
- **Document Embeddings**: Vector representations of text
- **Audio Files**: Temporary files (deleted after processing)

#### Data Retention

Configure data retention policies:

```python
from pebblemind.advanced_memory import LongTermMemory

memory = LongTermMemory()

# Configure automatic forgetting
await memory.forget_memories(
    importance_threshold=0.2,  # Forget low-importance memories
    age_threshold_days=30,     # Older than 30 days
    max_to_forget=10           # Limit deletion batch size
)
```

### Encryption at Rest

For sensitive deployments, encrypt the data directory:

```bash
# Using LUKS (Linux)
cryptsetup luksFormat /dev/sdX
cryptsetup open /dev/sdX pebblemind_data
mkfs.ext4 /dev/mapper/pebblemind_data
mount /dev/mapper/pebblemind_data /path/to/data

# Using eCryptfs (cross-platform)
ecryptfs-setup-private --noautomount
```

---

## Best Practices

### 1. Network Security

#### Firewall Configuration

```bash
# Allow only localhost (development)
sudo ufw allow from 127.0.0.1 to any port 8000

# Allow specific IP range (production)
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

#### Reverse Proxy with Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Access Control

#### Principle of Least Privilege

Run PebbleMind with minimal permissions:

```bash
# Create dedicated user
sudo useradd -r -s /bin/false pebblemind

# Set ownership
sudo chown -R pebblemind:pebblemind /opt/pebblemind

# Run as service
sudo systemctl start pebblemind
```

#### File Permissions

```bash
# Application code (read-only)
chmod 755 /opt/pebblemind
chmod 644 /opt/pebblemind/*.py

# Configuration files (read-only for app, write for admin)
chmod 600 .env
chmod 640 pebblemind.yaml

# Data directory (read-write for app only)
chmod 700 data/
chmod 600 data/*.db

# Log files (append-only)
chmod 640 logs/*.log
```

### 3. Input Sanitization

#### User Input Handling

PebbleMind automatically sanitizes inputs, but follow these guidelines:

```python
# Good - Let Pydantic handle validation
from pydantic import BaseModel, Field, validator

class UserInput(BaseModel):
    message: str = Field(..., max_length=10000)

    @validator('message')
    def sanitize_message(cls, v):
        # Remove control characters
        return ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')

# Bad - Direct string usage
user_message = request.get("message")  # No validation!
```

### 4. Dependency Management

#### Keep Dependencies Updated

```bash
# Check for security updates
pip list --outdated

# Update with constraints
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Audit for vulnerabilities
pip install safety
safety check
```

#### Pin Versions in Production

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
# ... pin all dependencies
```

### 5. Monitoring and Logging

#### Security Logging

Configure comprehensive logging:

```python
import logging

# In production, use structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)

# Log security events
logger.info("Authentication successful", extra={
    "event": "auth_success",
    "client_ip": client_ip,
    "timestamp": datetime.now().isoformat()
})
```

#### Monitoring Checklist

- [ ] Monitor failed authentication attempts
- [ ] Track rate limit violations
- [ ] Log file upload events
- [ ] Monitor database query performance
- [ ] Track API response times
- [ ] Alert on unusual patterns

---

## Security Updates

### Staying Informed

1. **Watch GitHub Repository**: https://github.com/yourusername/pebblemind
2. **Subscribe to Security Advisories**: Check GitHub Security tab
3. **Follow Release Notes**: Review CHANGELOG.md for security fixes

### Update Process

```bash
# Backup data first
cp -r data/ data.backup/

# Pull latest updates
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run database migrations (if any)
python scripts/migrate.py

# Restart service
sudo systemctl restart pebblemind

# Verify functionality
curl http://localhost:8000/health
```

---

## Reporting Security Issues

### Responsible Disclosure

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. **DO NOT** disclose the vulnerability publicly
3. **DO** email security details to: [security@example.com]
4. **DO** provide:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **24 hours**: Initial response acknowledging receipt
- **7 days**: Assessment and planned fix timeline
- **30 days**: Security patch released (target)
- **Public disclosure**: After patch is released and deployed

### Bug Bounty

Currently, we do not offer a bug bounty program, but we deeply appreciate security researchers who responsibly disclose vulnerabilities. Contributors will be credited in release notes (unless they prefer to remain anonymous).

---

## Security Checklist for Production Deployment

### Pre-Deployment

- [ ] Strong API keys generated and configured
- [ ] .env file secured with proper permissions (chmod 600)
- [ ] Debug mode disabled
- [ ] Specific CORS origins configured
- [ ] HTTPS enabled with valid certificates
- [ ] Rate limiting configured appropriately
- [ ] File permissions set correctly
- [ ] Database files secured (chmod 600)
- [ ] Dependencies updated and audited
- [ ] Monitoring and logging configured

### Post-Deployment

- [ ] Verify authentication is working
- [ ] Test rate limiting
- [ ] Check HTTPS certificate validity
- [ ] Monitor logs for suspicious activity
- [ ] Set up automated security scans
- [ ] Configure backup strategy
- [ ] Document incident response procedures
- [ ] Train team on security practices

---

## Additional Resources

### Security Tools

- **Safety**: Python dependency security scanner
  ```bash
  pip install safety
  safety check
  ```

- **Bandit**: Python security linter
  ```bash
  pip install bandit
  bandit -r pebblemind/
  ```

- **OWASP ZAP**: Web application security scanner
  - https://www.zaproxy.org/

### References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLite Security Best Practices](https://www.sqlite.org/security.html)

---

## License

This security guide is part of the PebbleMind project and is provided "as is" without warranty of any kind.

**Last Updated**: February 15, 2026
**Version**: 1.0.0
