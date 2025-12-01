# AIDE ML Enterprise - Deployment Guide

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB+ available space
- **OS**: Linux, macOS, or Windows with WSL2

### Software Requirements

- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher
- **npm**: 8.x or higher
- **Docker**: 20.x or higher (optional)
- **Docker Compose**: 2.x or higher (optional)

## Local Development

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd aideml

# 2. Run setup script
bash scripts/setup.sh

# 3. Configure API keys
# Edit .env file and add your API keys

# 4. Start development servers
make dev
```

### Manual Setup

#### Backend

```bash
# Install dependencies
pip install -e .
pip install -r backend/requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add API keys

# Initialize database
python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"

# Run backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Create .env file
cp .env.example .env

# Run development server
npm run dev
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Docker Deployment

### Quick Start with Docker Compose

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 2. Build and start containers
docker-compose up --build -d

# 3. View logs
docker-compose logs -f

# 4. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

### Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]

# Remove all containers and volumes
docker-compose down -v
```

## Production Deployment

### Environment Configuration

1. **Create production .env file**
   ```bash
   cp .env.example .env.production
   ```

2. **Edit .env.production with production values**
   ```env
   # Use strong secret key
   SECRET_KEY=your-strong-production-secret-key
   
   # Production database (can use PostgreSQL)
   DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
   
   # API Keys
   OPENAI_API_KEY=your-production-key
   
   # CORS origins
   BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
   ```

### Option 1: Docker Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Enable SSL/TLS (recommended)
# Use nginx or traefik as reverse proxy with Let's Encrypt
```

### Option 2: Manual Deployment

#### Backend Deployment

```bash
# Install dependencies
pip install -e .
pip install -r backend/requirements.txt
pip install gunicorn

# Run with gunicorn
gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

#### Frontend Deployment

```bash
# Build frontend
cd frontend
npm install
npm run build

# Serve with nginx
# Copy dist/ contents to nginx html directory
# Configure nginx as reverse proxy
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /var/www/aide-ml/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

### Systemd Service (Linux)

Create `/etc/systemd/system/aide-backend.service`:

```ini
[Unit]
Description=AIDE ML Backend
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/aide-ml
Environment="PATH=/opt/aide-ml/venv/bin"
ExecStart=/opt/aide-ml/venv/bin/gunicorn backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable aide-backend
sudo systemctl start aide-backend
sudo systemctl status aide-backend
```

## SSL/TLS Configuration

### Using Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

## Monitoring and Logging

### Application Logs

```bash
# Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Systemd logs
sudo journalctl -u aide-backend -f
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Check API documentation
curl http://localhost:8000/docs
```

## Database Backup

### SQLite Backup

```bash
# Backup database
cp data/aide.db backups/aide-$(date +%Y%m%d).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/aide"
mkdir -p $BACKUP_DIR
cp /app/data/aide.db $BACKUP_DIR/aide-$(date +%Y%m%d-%H%M%S).db

# Keep only last 30 days
find $BACKUP_DIR -name "aide-*.db" -mtime +30 -delete
```

## Scaling Considerations

### Horizontal Scaling

- Use PostgreSQL instead of SQLite for multi-instance deployments
- Implement Redis for session management
- Use load balancer (nginx, HAProxy) for multiple backend instances

### Performance Optimization

- Enable caching for static assets
- Use CDN for frontend assets
- Optimize database queries
- Monitor resource usage

## Security Best Practices

1. **API Keys**
   - Never commit API keys to version control
   - Use environment variables
   - Rotate keys regularly

2. **Database**
   - Use strong passwords
   - Enable SSL/TLS for database connections
   - Regular backups

3. **Network**
   - Use HTTPS in production
   - Configure firewall rules
   - Implement rate limiting

4. **Application**
   - Keep dependencies updated
   - Implement authentication for multi-user scenarios
   - Regular security audits

## Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip list | grep fastapi

# Check logs
docker-compose logs backend
```

#### Frontend build fails

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

#### Database connection errors

```bash
# Check database file permissions
ls -la data/aide.db

# Recreate database
rm data/aide.db
python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"
```

#### WebSocket connection fails

- Check firewall settings
- Verify CORS configuration
- Check nginx WebSocket proxy configuration

### Getting Help

- Check application logs
- Review error messages in browser console
- Consult API documentation at `/docs`
- Open GitHub issue with detailed error information

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and system resources
- **Weekly**: Check disk space, review error logs
- **Monthly**: Update dependencies, backup database
- **Quarterly**: Security audit, performance review

### Updates

```bash
# Pull latest changes
git pull origin main

# Update backend dependencies
pip install -r backend/requirements.txt --upgrade

# Update frontend dependencies
cd frontend
npm update

# Rebuild and restart
docker-compose up --build -d
```

---

For additional support, consult the main README or open an issue on GitHub.
