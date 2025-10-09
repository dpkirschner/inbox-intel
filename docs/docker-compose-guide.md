# Docker Compose Guide

## Overview

The `docker-compose.yml` file provides a complete, production-ready configuration for deploying InboxIntel.

## Configuration Breakdown

### Service Definition

```yaml
services:
  inbox-intel:
    build:
      context: .
      dockerfile: Dockerfile
    image: inbox-intel:latest
    container_name: inbox-intel
```

- **Build context**: Current directory (`.`)
- **Dockerfile**: Uses the multi-stage Dockerfile
- **Image name**: `inbox-intel:latest`
- **Container name**: `inbox-intel` (for easy reference)

### Restart Policy

```yaml
restart: unless-stopped
```

The container automatically restarts unless explicitly stopped:
- ✅ Restarts after system reboot
- ✅ Restarts after Docker daemon restart
- ✅ Restarts after container crashes
- ❌ Does NOT restart if manually stopped (`docker-compose stop`)

### Port Mapping

```yaml
ports:
  - "8000:8000"
```

Maps host port 8000 to container port 8000:
- Access webhook endpoint: `http://localhost:8000/webhooks/guesty/messages`
- Health check: `http://localhost:8000/`

### Volume Mounts

```yaml
volumes:
  - ./data:/app/data              # Database persistence
  - ./.env:/app/.env:ro           # Configuration (read-only)
```

#### Data Volume (`./data:/app/data`)

**Purpose**: Persist SQLite database across container restarts

**What it does**:
- Creates `./data` directory on host if it doesn't exist
- Mounts it to `/app/data` inside container
- Database file: `./data/inbox_intel.db`

**Benefits**:
- Database survives container deletion
- Easy backups (just copy `./data` directory)
- Can be inspected/modified from host

#### Environment File (`./.env:/app/.env:ro`)

**Purpose**: Provide configuration to application

**What it does**:
- Mounts `.env` file from host
- Read-only (`:ro`) - prevents container from modifying it
- All environment variables loaded by application

**Benefits**:
- Single source of truth for configuration
- Easy to update (edit `.env`, restart container)
- Secure (not baked into image)

### Environment Variables

```yaml
environment:
  - DATABASE_URL=sqlite:///data/inbox_intel.db
  - WEBHOOK_PORT=8000
```

These override values from `.env` file:
- **DATABASE_URL**: Points to database in mounted volume
- **WEBHOOK_PORT**: Ensures app listens on correct port

### Health Check

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/', timeout=2)"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 10s
```

Monitors container health:
- **Test**: HTTP GET to root endpoint
- **Interval**: Checks every 30 seconds
- **Timeout**: 3 seconds per check
- **Retries**: 3 failures before marking unhealthy
- **Start period**: 10 second grace period on startup

### Network

```yaml
networks:
  - inbox-intel-network
```

Creates isolated network for the service:
- Enables future expansion (add database, cache, etc.)
- Provides DNS resolution by service name
- Isolates from other Docker networks

## Usage

### First Time Setup

```bash
# 1. Create .env file
cp .env.example .env

# 2. Edit .env with your credentials
nano .env  # or vim, code, etc.

# 3. Create data directory (optional - auto-created)
mkdir -p data

# 4. Start the application
docker-compose up -d
```

### Verify Deployment

```bash
# Check container status
docker-compose ps

# Expected output:
#     Name                   Command               State           Ports
# ------------------------------------------------------------------------
# inbox-intel   python -m uvicorn src.mai ...   Up (healthy)   0.0.0.0:8000->8000/tcp

# View logs
docker-compose logs -f

# Check health
docker-compose ps
# Should show "Up (healthy)" status
```

### Common Operations

#### View Logs
```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail 100

# Logs since 1 hour ago
docker-compose logs --since 1h
```

#### Restart Container
```bash
# Restart (keeps container)
docker-compose restart

# Stop and remove container, then start fresh
docker-compose down && docker-compose up -d

# Rebuild image and restart
docker-compose up -d --build
```

#### Execute Commands
```bash
# Run backfill
docker-compose exec inbox-intel python backfill.py --days 30

# Access Python shell
docker-compose exec inbox-intel python

# Access container shell
docker-compose exec inbox-intel /bin/bash
```

#### Stop and Remove
```bash
# Stop container (data persists)
docker-compose stop

# Stop and remove container (data persists)
docker-compose down

# Stop, remove container AND volumes (data deleted!)
docker-compose down -v  # ⚠️ DANGER: Deletes database
```

## Data Persistence Verification

### Test Database Persistence

```bash
# 1. Start container
docker-compose up -d

# 2. Create test data
docker-compose exec inbox-intel python -c "
from src.database import init_database, get_engine, get_session, Message
from datetime import datetime, UTC
init_database('sqlite:///data/inbox_intel.db')
engine = get_engine('sqlite:///data/inbox_intel.db')
session = get_session(engine)
msg = Message(
    guesty_message_id='test_123',
    message_text='Test message',
    timestamp=datetime.now(UTC),
    is_processed=False
)
session.add(msg)
session.commit()
print('Message created!')
"

# 3. Stop and remove container
docker-compose down

# 4. Start container again
docker-compose up -d

# 5. Verify data persists
docker-compose exec inbox-intel python -c "
from src.database import get_engine, get_session, Message
from sqlalchemy import select
engine = get_engine('sqlite:///data/inbox_intel.db')
session = get_session(engine)
stmt = select(Message).where(Message.guesty_message_id == 'test_123')
msg = session.execute(stmt).scalar_one()
print(f'Message found: {msg.message_text}')
"
```

Expected output: `Message found: Test message`

## Configuration Management

### Update Configuration

```bash
# 1. Edit .env file
nano .env

# 2. Restart container to apply changes
docker-compose restart
```

### Environment Variable Priority

Variables are loaded in this order (later overrides earlier):

1. `.env` file (mounted)
2. `environment:` section in docker-compose.yml
3. Shell environment (when using `docker-compose`)

### Sensitive Data

**Never commit `.env` to version control!**

```bash
# Verify .env is in .gitignore
grep "\.env" .gitignore

# If not, add it
echo ".env" >> .gitignore
```

## Volume Management

### Backup Database

```bash
# Stop container (optional but recommended)
docker-compose stop

# Create backup
cp -r data data-backup-$(date +%Y%m%d)

# Or create compressed backup
tar -czf inbox-intel-backup-$(date +%Y%m%d).tar.gz data

# Restart container
docker-compose start
```

### Restore Database

```bash
# Stop container
docker-compose stop

# Restore from backup
rm -rf data
cp -r data-backup-20250108 data

# Start container
docker-compose start
```

### Inspect Volume

```bash
# View database file
ls -lh data/

# Check database size
du -sh data/inbox_intel.db

# Access database directly
sqlite3 data/inbox_intel.db "SELECT COUNT(*) FROM messages;"
```

## Production Considerations

### Recommended Modifications

```yaml
version: '3.8'

services:
  inbox-intel:
    image: inbox-intel:latest
    container_name: inbox-intel-prod
    restart: always  # More aggressive restart policy
    ports:
      - "127.0.0.1:8000:8000"  # Only expose to localhost
    volumes:
      - inbox-intel-data:/app/data  # Named volume
      - /secure/path/.env:/app/.env:ro
    environment:
      - DATABASE_URL=sqlite:///data/inbox_intel.db
      - LOG_LEVEL=WARNING  # Less verbose in production
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

volumes:
  inbox-intel-data:
    driver: local
```

### Named Volumes vs Bind Mounts

**Current (Bind Mount):**
```yaml
volumes:
  - ./data:/app/data
```
- ✅ Easy to access from host
- ✅ Simple backups
- ❌ OS-dependent (permissions can vary)

**Alternative (Named Volume):**
```yaml
volumes:
  - inbox-intel-data:/app/data

volumes:
  inbox-intel-data:
    driver: local
```
- ✅ Managed by Docker
- ✅ Better cross-platform compatibility
- ❌ Less direct access from host

### Resource Limits

Prevent container from consuming all resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # Max 1 CPU core
      memory: 512M     # Max 512MB RAM
    reservations:
      cpus: '0.25'     # Guaranteed 0.25 CPU
      memory: 256M     # Guaranteed 256MB RAM
```

### Logging Configuration

Prevent log files from growing indefinitely:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # Max 10MB per file
    max-file: "3"      # Keep 3 files max
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Port 8000 already in use
#    Solution: Change port in docker-compose.yml
#
# 2. .env file missing
#    Solution: cp .env.example .env
#
# 3. Permission denied on /app/data
#    Solution: chmod -R 755 data
```

### Database Locked

```bash
# Stop all containers
docker-compose down

# Check for stale lock files
ls -la data/*.db-*

# Remove lock files
rm -f data/*.db-journal data/*.db-wal

# Start container
docker-compose up -d
```

### Health Check Failing

```bash
# Check container logs
docker-compose logs

# Manually test endpoint
curl http://localhost:8000/

# Check if Python packages installed
docker-compose exec inbox-intel pip list | grep requests
```

### Volume Not Mounting

```bash
# Check volume mounts
docker inspect inbox-intel | jq '.[0].Mounts'

# Verify data directory exists
ls -la data/

# Create if missing
mkdir -p data && chmod 755 data

# Recreate container
docker-compose up -d --force-recreate
```

## Advanced Usage

### Multiple Environments

**Development:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Production:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Override File Example

`docker-compose.override.yml` (auto-loaded):
```yaml
version: '3.8'

services:
  inbox-intel:
    environment:
      - LOG_LEVEL=DEBUG
    volumes:
      - ./src:/app/src  # Mount source for live reload
```

### Scale Services (Future)

```bash
# Run multiple instances (requires load balancer)
docker-compose up -d --scale inbox-intel=3
```

## Summary

The `docker-compose.yml` provides:

✅ **Single command deployment** - `docker-compose up -d`
✅ **Data persistence** - SQLite database survives restarts
✅ **Configuration management** - `.env` file for all settings
✅ **Health monitoring** - Built-in health checks
✅ **Production ready** - Restart policies, logging, resource limits
✅ **Easy maintenance** - Simple commands for logs, backups, updates

For quick reference, see [DOCKER_QUICKSTART.md](../DOCKER_QUICKSTART.md).
