# Docker Deployment Guide

This guide covers how to build and deploy InboxIntel using Docker.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later (optional, for docker-compose deployment)
- At least 512MB of available RAM
- 1GB of disk space

## Quick Start

### Using Docker Compose (Recommended)

1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Start the application:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Using Docker CLI

1. **Build the image:**
   ```bash
   docker build -t inbox-intel:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name inbox-intel \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/.env:/app/.env:ro \
     --restart unless-stopped \
     inbox-intel:latest
   ```

3. **View logs:**
   ```bash
   docker logs -f inbox-intel
   ```

## Dockerfile Architecture

The Dockerfile uses a **multi-stage build** pattern for optimal image size and security:

### Stage 1: Builder
- Base: `python:3.11-slim`
- Installs build dependencies (gcc)
- Creates virtual environment
- Installs Python dependencies
- Final size: ~200MB (discarded)

### Stage 2: Runtime
- Base: `python:3.11-slim`
- Copies only the virtual environment from builder
- Adds application code
- Creates non-root user for security
- Final size: ~150MB

### Key Features

✅ **Multi-stage build** - Reduces final image size by 50%+
✅ **Non-root user** - Runs as `appuser` (UID 10001)
✅ **Health check** - Automatic container health monitoring
✅ **Layer caching** - Optimized for fast rebuilds
✅ **Security** - Minimal attack surface with slim base image

## Configuration

### Environment Variables

All configuration is done via environment variables in `.env`:

```bash
# Guesty API
GUESTY_API_KEY=your_api_key
GUESTY_API_SECRET=your_api_secret

# Database
DATABASE_URL=sqlite:///data/inbox_intel.db

# LLM
LLM_PROVIDER=openai:gpt-4-turbo
OPENAI_API_KEY=your_openai_key

# Notifications
PUSHOVER_TOKEN=your_token
PUSHOVER_USER=your_user_key

# Scheduler
REPORT_HOUR=7
POLLING_INTERVAL_MINUTES=5
PROCESSING_INTERVAL_SECONDS=30

# Application
WEBHOOK_PORT=8000
LOG_LEVEL=INFO
```

### Volume Mounts

The container uses two volumes:

1. **`./data:/app/data`** - Persistent database storage
2. **`./.env:/app/.env:ro`** - Configuration (read-only)

## Running Commands Inside Container

### Backfill Historical Data

```bash
# Using docker-compose
docker-compose exec inbox-intel python backfill.py --days 30

# Using docker CLI
docker exec -it inbox-intel python backfill.py --days 30
```

### Access Python Shell

```bash
docker exec -it inbox-intel python
```

### View Application Logs

```bash
# Real-time logs
docker logs -f inbox-intel

# Last 100 lines
docker logs --tail 100 inbox-intel

# Logs since 1 hour ago
docker logs --since 1h inbox-intel
```

## Advanced Configuration

### Custom Port Mapping

Change the exposed port in `docker-compose.yml`:

```yaml
ports:
  - "3000:8000"  # Access on localhost:3000
```

Or with Docker CLI:

```bash
docker run -p 3000:8000 inbox-intel:latest
```

### Resource Limits

Add resource constraints in `docker-compose.yml`:

```yaml
services:
  inbox-intel:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Environment-Specific Builds

Build with different base images:

```dockerfile
# Development with debug tools
FROM python:3.11 AS builder

# Production with minimal image
FROM python:3.11-slim AS builder
```

## Health Monitoring

The container includes a built-in health check:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' inbox-intel

# View health check logs
docker inspect --format='{{json .State.Health}}' inbox-intel | jq
```

Health check criteria:
- **Interval:** 30 seconds
- **Timeout:** 3 seconds
- **Start period:** 10 seconds
- **Retries:** 3

## Networking

### Connect to External Services

The default bridge network works for most cases. For advanced networking:

```yaml
services:
  inbox-intel:
    networks:
      - frontend
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### Webhook Configuration

If using a reverse proxy (nginx, Caddy, Traefik):

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.inbox-intel.rule=Host(`inbox.example.com`)"
  - "traefik.http.services.inbox-intel.loadbalancer.server.port=8000"
```

## Troubleshooting

### Container Won't Start

1. **Check logs:**
   ```bash
   docker logs inbox-intel
   ```

2. **Verify environment variables:**
   ```bash
   docker exec inbox-intel env | grep GUESTY
   ```

3. **Check database permissions:**
   ```bash
   docker exec inbox-intel ls -la /app/data
   ```

### High Memory Usage

Monitor resource usage:

```bash
docker stats inbox-intel
```

Optimize by:
- Reducing `PROCESSING_INTERVAL_SECONDS`
- Limiting backfill scope
- Using a smaller LLM model

### Database Issues

Access the database:

```bash
docker exec -it inbox-intel sqlite3 /app/data/inbox_intel.db
```

Common queries:
```sql
-- Check message count
SELECT COUNT(*) FROM messages;

-- Check unprocessed messages
SELECT COUNT(*) FROM messages WHERE is_processed = 0;

-- View recent messages
SELECT * FROM messages ORDER BY timestamp DESC LIMIT 10;
```

### Rebuild Without Cache

Force a fresh build:

```bash
docker-compose build --no-cache
```

Or with Docker CLI:

```bash
docker build --no-cache -t inbox-intel:latest .
```

## Production Deployment

### Recommended Setup

1. **Use docker-compose.yml for configuration**
2. **Store .env securely** (not in version control)
3. **Mount data volume** for database persistence
4. **Enable restart policy** (`unless-stopped` or `always`)
5. **Configure logging driver** for centralized logs
6. **Set up monitoring** with health checks
7. **Use HTTPS** with reverse proxy

### Example Production Compose

```yaml
version: '3.8'

services:
  inbox-intel:
    image: inbox-intel:latest
    container_name: inbox-intel
    restart: always
    ports:
      - "127.0.0.1:8000:8000"  # Only expose to localhost
    volumes:
      - inbox-intel-data:/app/data
      - /secure/path/.env:/app/.env:ro
    environment:
      - DATABASE_URL=sqlite:///data/inbox_intel.db
      - LOG_LEVEL=WARNING
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/', timeout=2)"]
      interval: 60s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

volumes:
  inbox-intel-data:
    driver: local

networks:
  default:
    name: inbox-intel-network
```

## Updates and Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# Or with Docker CLI
docker build -t inbox-intel:latest .
docker stop inbox-intel
docker rm inbox-intel
docker run -d --name inbox-intel ... inbox-intel:latest
```

### Backup Database

```bash
# Create backup
docker exec inbox-intel sqlite3 /app/data/inbox_intel.db ".backup '/app/data/backup.db'"

# Copy to host
docker cp inbox-intel:/app/data/backup.db ./backup-$(date +%Y%m%d).db
```

### Restore Database

```bash
# Copy backup to container
docker cp backup-20250108.db inbox-intel:/app/data/restore.db

# Restore
docker exec inbox-intel sqlite3 /app/data/inbox_intel.db ".restore '/app/data/restore.db'"
```

## Security Best Practices

1. **Never commit .env** - Add to `.gitignore`
2. **Use read-only mounts** - `.env` file mounted as `:ro`
3. **Run as non-root** - Dockerfile creates `appuser`
4. **Limit network exposure** - Bind to `127.0.0.1` if using reverse proxy
5. **Keep base image updated** - Rebuild regularly for security patches
6. **Scan for vulnerabilities** - Use `docker scan inbox-intel:latest`
7. **Use secrets** - For production, use Docker secrets or Kubernetes secrets

## Monitoring

### Prometheus Metrics

Expose metrics endpoint by adding to `main.py`:

```python
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### Log Aggregation

Configure external logging:

```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logserver:514"
    tag: "inbox-intel"
```

## Performance Optimization

### Build Time Optimization

1. **Use .dockerignore** - Exclude unnecessary files
2. **Order layers strategically** - Dependencies before source code
3. **Leverage BuildKit cache** - `DOCKER_BUILDKIT=1 docker build`

### Runtime Optimization

1. **Use slim base images** - `python:3.11-slim` vs `python:3.11`
2. **Multi-stage builds** - Separate build and runtime environments
3. **Install only runtime deps** - No build tools in final image

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Security Scanning](https://docs.docker.com/engine/scan/)
