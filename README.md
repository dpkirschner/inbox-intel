# InboxIntel

**A self-hosted service for intelligent monitoring of Guesty guest messages**

InboxIntel connects to your Guesty property management system to automatically monitor guest messages, classify them using AI, and send real-time alerts for important requests like early check-ins, late checkouts, and maintenance issues.

[![Tests](https://img.shields.io/badge/tests-117%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

🔔 **Real-time Notifications** - Instant alerts via Pushover, Slack, or Email for priority messages

🤖 **AI-Powered Classification** - Automatically categorizes messages:
- Early check-in requests
- Late checkout requests
- Special requests (extra amenities)
- Maintenance issues
- General questions

📊 **Daily Reports** - Morning summaries of arrivals and their special requests

📥 **Webhook Integration** - Real-time message ingestion from Guesty

🔄 **Polling Fallback** - Automatic backup polling to catch any missed messages

📜 **Historical Backfill** - Import and classify past messages for trend analysis

🐳 **Docker Ready** - One-command deployment with Docker Compose

🔒 **Self-Hosted** - Your data stays under your control

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Guesty account with API access
- OpenAI API key (or local Ollama instance)
- Pushover, Slack, or Email for notifications

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/inbox-intel.git
cd inbox-intel
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required: Guesty API credentials
GUESTY_API_KEY=your_api_key_here
GUESTY_API_SECRET=your_api_secret_here

# Required: LLM for classification
LLM_PROVIDER=openai:gpt-4-turbo
OPENAI_API_KEY=your_openai_api_key_here

# Required: At least one notification channel
PUSHOVER_TOKEN=your_pushover_app_token
PUSHOVER_USER=your_pushover_user_key

# Optional: Additional notification channels
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EMAIL_FROM=noreply@example.com
EMAIL_TO=you@example.com

# Optional: Customize schedule
REPORT_HOUR=7                      # Daily report at 7:00 AM
POLLING_INTERVAL_MINUTES=5         # Poll Guesty every 5 minutes
PROCESSING_INTERVAL_SECONDS=30     # Process messages every 30 seconds
```

<details>
<summary><strong>📋 Click to see all available configuration options</strong></summary>

```bash
# ============================================
# Guesty API Configuration
# ============================================
GUESTY_API_KEY=your_api_key_here
GUESTY_API_SECRET=your_api_secret_here
GUESTY_API_BASE_URL=https://api.guesty.com/v1

# ============================================
# Database Configuration
# ============================================
DATABASE_URL=sqlite:///data/inbox_intel.db

# ============================================
# LLM Configuration
# ============================================
# Options:
# - openai:gpt-4-turbo (recommended)
# - openai:gpt-3.5-turbo (faster, cheaper)
# - ollama:llama3 (local, free)
LLM_PROVIDER=openai:gpt-4-turbo
OPENAI_API_KEY=your_openai_api_key_here

# ============================================
# Notification Configuration
# ============================================
# Pushover (mobile push notifications)
PUSHOVER_TOKEN=your_pushover_app_token
PUSHOVER_USER=your_pushover_user_key

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email
EMAIL_FROM=noreply@example.com
EMAIL_TO=you@example.com
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=smtp_username
EMAIL_SMTP_PASSWORD=smtp_password

# ============================================
# Scheduler Configuration
# ============================================
POLLING_INTERVAL_MINUTES=5         # How often to poll Guesty API
PROCESSING_INTERVAL_SECONDS=30     # How often to process messages
REPORT_HOUR=7                      # Daily report time (24-hour format)

# ============================================
# Alert Configuration
# ============================================
# Comma-separated list of categories to alert on
ALERT_CATEGORIES=EARLY_CHECKIN,LATE_CHECKOUT,MAINTENANCE_ISSUE,SPECIAL_REQUEST

# Minimum confidence score (0.0-1.0) to trigger alerts
MIN_CONFIDENCE_THRESHOLD=0.7

# ============================================
# Historical Data Configuration
# ============================================
BACKFILL_DAYS=365                  # Default days for backfill script

# ============================================
# Application Configuration
# ============================================
DATA_DIR=data
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
WEBHOOK_PORT=8000
```

</details>

### 3. Build and Run with Docker Compose

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

That's it! InboxIntel is now running and monitoring your Guesty messages.

### 4. Import Historical Messages (Optional)

Backfill past messages for analysis:

```bash
# Import last 30 days
docker-compose exec inbox-intel python backfill.py --days 30

# Import last year
docker-compose exec inbox-intel python backfill.py --days 365

# Import last week (good for testing)
docker-compose exec inbox-intel python backfill.py --days 7
```

The backfill script will:
- Fetch messages from Guesty API
- Save them to the database
- Automatically classify them in the background

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        Guesty API                            │
│              (Webhooks + REST Endpoints)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌──────────────┐
│   Webhook     │         │   Polling    │
│   Receiver    │         │   Worker     │
└───────┬───────┘         └──────┬───────┘
        │                         │
        └────────────┬────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  SQLite Database │
            └────────┬─────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  Classification  │
            │     Worker       │
            │  (LLM-powered)   │
            └────────┬─────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Pushover │  │  Slack   │  │  Email   │
└──────────┘  └──────────┘  └──────────┘
```

## Configuration Guide

### Step 1: Get Guesty API Credentials

1. Log into your Guesty account
2. Navigate to **Settings** → **API & Webhooks**
3. Click **Create API Key**
4. Save your `API Key` and `API Secret`
5. Add them to your `.env` file:
   ```bash
   GUESTY_API_KEY=your_api_key_here
   GUESTY_API_SECRET=your_api_secret_here
   ```

### Step 2: Get OpenAI API Key

1. Create account at [platform.openai.com](https://platform.openai.com)
2. Navigate to **API Keys**
3. Click **Create new secret key**
4. Save the key and add to `.env`:
   ```bash
   OPENAI_API_KEY=sk-...your_key_here
   ```

Alternatively, use a local LLM (Ollama):
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3

# Update .env
LLM_PROVIDER=ollama:llama3
# Remove OPENAI_API_KEY
```

### Step 3: Set Up Notifications

**Option A: Pushover (Recommended for mobile)**

1. Create account at [pushover.net](https://pushover.net)
2. Create an application (e.g., "InboxIntel")
3. Note your **User Key** and **Application Token**
4. Add to `.env`:
   ```bash
   PUSHOVER_TOKEN=your_app_token
   PUSHOVER_USER=your_user_key
   ```

**Option B: Slack**

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Incoming Webhooks**
3. Create a webhook for your channel
4. Add to `.env`:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

**Option C: Email**

Add SMTP credentials to `.env`:
```bash
EMAIL_FROM=noreply@yourdomain.com
EMAIL_TO=you@yourdomain.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your_email@gmail.com
EMAIL_SMTP_PASSWORD=your_app_password
```

## Using Docker Compose

### Build and Start

```bash
# Build and start in detached mode
docker-compose up -d --build

# View logs in real-time
docker-compose logs -f
```

### Stop and Restart

```bash
# Stop containers (data persists)
docker-compose stop

# Start stopped containers
docker-compose start

# Restart containers
docker-compose restart

# Stop and remove containers (data persists in ./data)
docker-compose down
```

### View Status and Logs

```bash
# Check container status
docker-compose ps

# View logs (last 100 lines)
docker-compose logs --tail 100

# Follow logs in real-time
docker-compose logs -f

# View logs since 1 hour ago
docker-compose logs --since 1h
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Running the Backfill Script

The backfill script imports historical messages from Guesty.

### Basic Usage

```bash
# Run with default days (365 from config)
docker-compose exec inbox-intel python backfill.py

# Run with custom number of days
docker-compose exec inbox-intel python backfill.py --days 30
```

### Examples

```bash
# Import last week (good for testing)
docker-compose exec inbox-intel python backfill.py --days 7

# Import last 30 days
docker-compose exec inbox-intel python backfill.py --days 30

# Import last 3 months
docker-compose exec inbox-intel python backfill.py --days 90

# Import last year
docker-compose exec inbox-intel python backfill.py --days 365
```

### What It Does

1. **Fetches** messages from Guesty API for specified time period
2. **Saves** them to local database (skips duplicates automatically)
3. **Classifies** messages in background via worker

### Output Example

```
Starting backfill for 30 days
Fetching batch: skip=0, limit=100
Fetched 100 messages (total available: 250)
Fetching batch: skip=100, limit=100
Fetched 100 messages (total available: 250)
Fetching batch: skip=200, limit=100
Fetched 50 messages (total available: 250)

==================================================
BACKFILL COMPLETE
==================================================
Total messages fetched: 250
New messages saved:     245
Duplicates skipped:     5
==================================================

Note: Saved messages will be processed and classified
by the worker automatically.
```

### Features

✅ **Safe to run multiple times** - Automatically skips duplicates
✅ **Handles pagination** - Works with any number of messages
✅ **Background processing** - Classification happens automatically
✅ **Error resilient** - Skips invalid messages gracefully

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Verify .env file exists
ls .env || cp .env.example .env

# Check if port 8000 is available
lsof -i :8000

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### No notifications being sent

```bash
# Test Pushover manually
docker-compose exec inbox-intel python -c "
from src.notifications import send_pushover_alert
send_pushover_alert('Test', 'InboxIntel is working!', priority=0)
"

# Verify configuration
docker-compose exec inbox-intel python -c "
from src.config import config
print('Pushover token configured:', bool(config.PUSHOVER_TOKEN))
print('Alert categories:', config.ALERT_CATEGORIES)
"
```

### Messages not being classified

```bash
# Check for unprocessed messages
docker-compose exec inbox-intel python -c "
from src.database import get_engine, get_session, Message
engine = get_engine('sqlite:///data/inbox_intel.db')
session = get_session(engine)
count = session.query(Message).filter_by(is_processed=False).count()
print(f'Unprocessed messages: {count}')
"

# Manually trigger processing
docker-compose exec inbox-intel python -c "
from src.worker import process_unclassified_messages
process_unclassified_messages()
"
```

## Advanced Usage

### Access Database

```bash
# Open SQLite shell
docker-compose exec inbox-intel sqlite3 /app/data/inbox_intel.db

# Quick queries
docker-compose exec inbox-intel sqlite3 /app/data/inbox_intel.db \
  "SELECT COUNT(*) FROM messages;"

docker-compose exec inbox-intel sqlite3 /app/data/inbox_intel.db \
  "SELECT * FROM messages WHERE llm_category='EARLY_CHECKIN' LIMIT 5;"
```

### Backup Database

```bash
# Create backup
docker-compose exec inbox-intel sqlite3 /app/data/inbox_intel.db \
  ".backup '/app/data/backup.db'"

# Copy to host
docker cp inbox-intel:/app/data/backup.db ./backup-$(date +%Y%m%d).db
```

### Custom Notification Templates

Edit templates in `templates/` directory:

```bash
# Edit early check-in template
nano templates/early_checkin_alert.md
```

Available variables: `{guest_name}`, `{reservation_id}`, `{confidence}`, `{summary}`, `{message_text}`

## Project Structure

```
inbox-intel/
├── src/                          # Application source code
│   ├── main.py                  # FastAPI server & scheduler
│   ├── guesty_client.py         # Guesty API client
│   ├── database.py              # Database models
│   ├── llm_classifier.py        # LLM classification
│   ├── notifications.py         # Alert system
│   ├── reporter.py              # Daily summaries
│   ├── worker.py                # Message processor
│   ├── polling.py               # Polling mechanism
│   ├── backfill.py              # Historical import
│   ├── config.py                # Configuration
│   └── logger.py                # Logging
├── templates/                    # Notification templates
├── tests/                        # Test suite (117 tests)
├── docs/                         # Documentation
├── data/                         # Database storage
├── Dockerfile                    # Multi-stage build
├── docker-compose.yml           # Deployment config
├── .env.example                 # Config template
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## Documentation

- **[Docker Guide](docs/docker.md)** - Comprehensive Docker deployment
- **[Docker Compose Guide](docs/docker-compose-guide.md)** - Detailed compose reference
- **[Backfill Guide](docs/backfill.md)** - Historical data import
- **[Product Requirements](docs/product.md)** - Full feature specifications
- **[Quick Start](DOCKER_QUICKSTART.md)** - 3-step deployment guide

## Performance

Typical resource usage:
- **Memory**: 100-200MB
- **CPU**: <5% (idle), 20-40% (processing)
- **Disk**: ~1-2KB per message

Handles:
- **Messages**: 10,000+ messages
- **Webhooks**: 10-20 requests/second
- **Classification**: 2-3 messages/second

## Security

✅ Non-root user in container
✅ Read-only config mounts
✅ Minimal base image
✅ No hardcoded secrets
✅ Environment-based config
✅ Self-hosted data

## Support

- 📖 **Documentation**: [docs/](docs/) directory
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions

## License

MIT License - see [LICENSE](LICENSE) file

---

**Made with ❤️ for property managers**
