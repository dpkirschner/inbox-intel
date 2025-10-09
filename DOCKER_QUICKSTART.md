# Docker Quick Start Guide

Get InboxIntel running in Docker in 3 simple steps.

## Prerequisites

- Docker installed and running
- `.env` file configured (copy from `.env.example`)

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env with your Guesty API credentials and notification settings

# 2. Start the application
docker-compose up -d

# 3. View logs
docker-compose logs -f inbox-intel

# Check health
docker-compose ps
```

Access the application at http://localhost:8000

### Option 2: Docker CLI

```bash
# 1. Build the image
docker build -t inbox-intel:latest .

# 2. Run the container
docker run -d \
  --name inbox-intel \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  inbox-intel:latest

# 3. View logs
docker logs -f inbox-intel
```

## Common Operations

### Backfill Historical Messages

```bash
# Using docker-compose
docker-compose exec inbox-intel python backfill.py --days 30

# Using docker CLI
docker exec -it inbox-intel python backfill.py --days 30
```

### Stop the Application

```bash
# docker-compose
docker-compose down

# docker CLI
docker stop inbox-intel && docker rm inbox-intel
```

### Restart the Application

```bash
# docker-compose
docker-compose restart

# docker CLI
docker restart inbox-intel
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail 100

# Specific time range
docker-compose logs --since 1h
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Troubleshooting

### Check Container Status

```bash
docker-compose ps
# or
docker ps -a | grep inbox-intel
```

### Check Health

```bash
docker inspect --format='{{.State.Health.Status}}' inbox-intel
```

### Access Container Shell

```bash
docker exec -it inbox-intel /bin/bash
```

### Check Database

```bash
docker exec -it inbox-intel sqlite3 /app/data/inbox_intel.db "SELECT COUNT(*) FROM messages;"
```

## Configuration

All configuration is done via the `.env` file. Required variables:

- `GUESTY_API_KEY` - Your Guesty API key
- `GUESTY_API_SECRET` - Your Guesty API secret
- `OPENAI_API_KEY` - OpenAI API key (for LLM)
- `PUSHOVER_TOKEN` / `PUSHOVER_USER` - For notifications

See `.env.example` for all available options.

## Data Persistence

The database is stored in the `./data` directory, which is mounted as a volume. Your data persists even when the container is stopped or removed.

## For More Information

See [docs/docker.md](docs/docker.md) for comprehensive Docker deployment documentation.
