# Historical Data Backfill

The backfill script allows you to ingest historical messages from your Guesty account into InboxIntel.

## Overview

The backfill process:
1. Fetches messages from Guesty API for the specified time period
2. Saves them to the local database (skips duplicates)
3. The existing worker automatically processes and classifies these messages

## Usage

### Basic Usage

Backfill the default number of days (365, configured via `BACKFILL_DAYS`):

```bash
python backfill.py
```

### Custom Time Period

Backfill a specific number of days:

```bash
python backfill.py --days 30
```

Backfill the last 7 days:

```bash
python backfill.py --days 7
```

### Running in Docker

If running InboxIntel in Docker:

```bash
docker exec -it inbox-intel python backfill.py --days 30
```

## Output

The script provides detailed progress information:

```
2025-01-08 10:00:00 - inbox_intel - INFO - Starting backfill for 30 days
2025-01-08 10:00:00 - inbox_intel - INFO - Fetching batch: skip=0, limit=100
2025-01-08 10:00:01 - inbox_intel - INFO - Fetched 100 messages (total available: 250)
2025-01-08 10:00:02 - inbox_intel - INFO - Fetching batch: skip=100, limit=100
2025-01-08 10:00:03 - inbox_intel - INFO - Fetched 100 messages (total available: 250)
2025-01-08 10:00:04 - inbox_intel - INFO - Fetching batch: skip=200, limit=100
2025-01-08 10:00:05 - inbox_intel - INFO - Fetched 50 messages (total available: 250)

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

## Features

### Automatic Pagination
- Handles large datasets by fetching in batches of 100 messages
- Automatically requests additional pages until all messages are retrieved

### Duplicate Detection
- Skips messages that already exist in the database
- Based on unique Guesty `messageId`
- Safe to run multiple times without creating duplicates

### Error Handling
- Invalid timestamps are handled gracefully
- Messages without required fields are skipped with warnings
- API errors are logged and propagated

### Background Processing
- Backfilled messages are marked as `is_processed=False`
- The existing worker picks them up automatically
- Classification happens in the background without blocking

## Configuration

The backfill script respects the following environment variables:

- `GUESTY_API_KEY` - Your Guesty API key (required)
- `GUESTY_API_SECRET` - Your Guesty API secret (required)
- `DATABASE_URL` - Database connection string (default: `sqlite:///data/inbox_intel.db`)
- `BACKFILL_DAYS` - Default number of days (default: 365)

## Performance Considerations

### Large Datasets
For accounts with many messages:
- Start with a smaller time period (e.g., 7-30 days)
- Monitor API rate limits
- Run during off-peak hours if possible

### Processing Time
- Fetching messages is typically fast (seconds to minutes)
- LLM classification happens asynchronously in the background
- Large backfills may take hours to fully classify

### Database Growth
Each message stores:
- Original message text
- Metadata (guest, reservation, timestamps)
- Classification results (category, summary, confidence)

Estimate ~1-2KB per message for storage planning.

## Troubleshooting

### No messages found
- Check your Guesty API credentials
- Verify the time period contains messages
- Review logs for API errors

### Duplicate messages
- This is expected behavior - the script safely skips duplicates
- Check the "Duplicates skipped" count in the output

### Classification not happening
- Ensure the main application is running (worker must be active)
- Check `PROCESSING_INTERVAL_SECONDS` configuration
- Review worker logs for errors

## Examples

### One-time historical import
```bash
# Import all messages from the past year
python backfill.py --days 365
```

### Regular top-ups
```bash
# Weekly: catch any missed messages
python backfill.py --days 7
```

### Testing
```bash
# Import just the last day for testing
python backfill.py --days 1
```

## Integration with Scheduler

You can optionally add backfill as a scheduled task to catch any messages that might have been missed by webhooks:

```python
# In main.py lifespan
_scheduler.add_job(
    lambda: backfill_messages(days=7),
    trigger="cron",
    day_of_week="sun",
    hour=2,
    minute=0,
    id="weekly_backfill",
    name="Weekly backfill for missed messages",
)
```

This runs a 7-day backfill every Sunday at 2:00 AM as a safety net.
