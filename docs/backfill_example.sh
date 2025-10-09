#!/bin/bash
# Example backfill script usage

# Backfill with default configuration (365 days)
python backfill.py

# Backfill last 30 days
python backfill.py --days 30

# Backfill last week (useful for catching missed webhook messages)
python backfill.py --days 7

# Backfill yesterday only
python backfill.py --days 1

# Run in verbose mode (shows all debug logs)
LOG_LEVEL=DEBUG python backfill.py --days 7
