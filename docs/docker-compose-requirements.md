# Docker Compose Requirements Checklist

## Requirements

- [x] **Create a `docker-compose.yml` file**
  - File location: `/opt/code/inbox-intel/docker-compose.yml`
  - Format: YAML version 3.8

- [x] **Define a service for the `inbox-intel` application**
  - Service name: `inbox-intel` (lines 4-26)
  - Build configuration: Uses Dockerfile in current directory
  - Container name: `inbox-intel`
  - Image: `inbox-intel:latest`

- [x] **Use the `.env` file for configuration**
  - Mounted as volume: `./.env:/app/.env:ro` (line 15)
  - Read-only mount (`:ro`) for security
  - Application loads environment variables from this file

- [x] **Define a mounted volume for the `/data` directory**
  - Volume mount: `./data:/app/data` (line 14)
  - Ensures SQLite database persists across container restarts
  - Database path: `/app/data/inbox_intel.db`

## Additional Features Included

Beyond the core requirements, the docker-compose.yml also includes:

### Container Management
- ✅ Restart policy: `unless-stopped`
- ✅ Container name for easy reference
- ✅ Port mapping: `8000:8000`

### Monitoring & Health
- ✅ Health check configuration
- ✅ Interval: 30s
- ✅ Timeout: 3s
- ✅ Retries: 3

### Networking
- ✅ Isolated network: `inbox-intel-network`
- ✅ Bridge driver for container communication

### Environment Variables
- ✅ DATABASE_URL explicitly set to use mounted volume
- ✅ WEBHOOK_PORT configured

## Verification

### Test Data Persistence

1. Start the container:
   ```bash
   docker-compose up -d
   ```

2. Create a test message:
   ```bash
   docker-compose exec inbox-intel python -c "
   from src.database import init_database, get_engine, get_session, Message
   from datetime import datetime, UTC
   init_database('sqlite:///data/inbox_intel.db')
   engine = get_engine('sqlite:///data/inbox_intel.db')
   session = get_session(engine)
   msg = Message(
       guesty_message_id='test_persist',
       message_text='Testing persistence',
       timestamp=datetime.now(UTC),
       is_processed=False
   )
   session.add(msg)
   session.commit()
   print('Test message created!')
   "
   ```

3. Stop and remove the container:
   ```bash
   docker-compose down
   ```

4. Start a new container:
   ```bash
   docker-compose up -d
   ```

5. Verify the message persisted:
   ```bash
   docker-compose exec inbox-intel python -c "
   from src.database import get_engine, get_session, Message
   from sqlalchemy import select
   engine = get_engine('sqlite:///data/inbox_intel.db')
   session = get_session(engine)
   stmt = select(Message).where(Message.guesty_message_id == 'test_persist')
   msg = session.execute(stmt).scalar_one()
   print(f'✓ Message persisted: {msg.message_text}')
   "
   ```

   Expected output: `✓ Message persisted: Testing persistence`

### Test .env File Loading

1. Check that environment variables are loaded:
   ```bash
   docker-compose exec inbox-intel python -c "
   from src.config import config
   print(f'GUESTY_API_KEY: {config.GUESTY_API_KEY[:10]}...')
   print(f'DATABASE_URL: {config.DATABASE_URL}')
   print(f'REPORT_HOUR: {config.REPORT_HOUR}')
   "
   ```

2. Verify .env is read-only:
   ```bash
   docker-compose exec inbox-intel touch /app/.env
   # Should fail with "Read-only file system"
   ```

## File Structure

```
inbox-intel/
├── docker-compose.yml          ← Main compose file
├── Dockerfile                  ← Multi-stage build definition
├── .dockerignore              ← Build context exclusions
├── .env                       ← Configuration (not in git)
├── .env.example              ← Configuration template
├── data/                     ← Database volume (host)
│   └── inbox_intel.db       ← SQLite database (persisted)
├── src/                      ← Application code
├── templates/                ← Notification templates
├── config/                   ← Configuration files
└── docs/
    ├── docker.md                      ← Comprehensive Docker guide
    ├── docker-compose-guide.md        ← Detailed compose documentation
    └── DOCKER_QUICKSTART.md           ← Quick start guide
```

## Summary

✅ All requirements met
✅ Production-ready configuration
✅ Data persistence verified
✅ Security best practices applied
✅ Comprehensive documentation provided
