"""Historical data backfill script for ingesting past messages from Guesty."""

import argparse
import sys
from datetime import UTC, datetime, timedelta

from .config import config
from .database import get_engine, get_session, init_database, save_message_from_webhook
from .guesty_client import GuestyClient
from .logger import logger


def backfill_messages(days: int) -> dict[str, int]:
    """
    Backfill messages from Guesty API for the specified number of days.

    Args:
        days: Number of days to look back for messages

    Returns:
        Dictionary with statistics: total_fetched, new_saved, duplicates_skipped
    """
    if days <= 0:
        raise ValueError("Days must be a positive integer")

    client = GuestyClient()
    engine = get_engine(config.DATABASE_URL)
    init_database(config.DATABASE_URL)
    session = get_session(engine)

    cutoff_time = datetime.now(UTC) - timedelta(days=days)
    logger.info(f"Starting backfill for messages since {cutoff_time.isoformat()}")

    stats = {
        "total_fetched": 0,
        "new_saved": 0,
        "duplicates_skipped": 0,
    }

    try:
        skip = 0
        limit = 100
        has_more = True

        while has_more:
            logger.info(f"Fetching batch: skip={skip}, limit={limit}")

            params = {
                "createdFrom": cutoff_time.isoformat(),
                "limit": limit,
                "skip": skip,
                "sort": "createdAt",
            }

            response = client._make_request(
                "GET", "communication/conversations/messages", params=params
            )

            messages_data = response.get("results", [])
            total_count = response.get("count", 0)

            logger.info(
                f"Fetched {len(messages_data)} messages (total available: {total_count})"
            )

            if not messages_data:
                has_more = False
                break

            for msg in messages_data:
                message_id = msg.get("_id")
                message_text = msg.get("body", "")
                created_at_str = msg.get("createdAt")

                if not message_id:
                    logger.warning("Message missing '_id', skipping")
                    continue

                stats["total_fetched"] += 1

                try:
                    if created_at_str:
                        timestamp = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                    else:
                        timestamp = datetime.now(UTC)
                except (ValueError, AttributeError) as e:
                    logger.error(f"Failed to parse timestamp for {message_id}: {e}")
                    timestamp = datetime.now(UTC)

                conversation_id = msg.get("conversationId")
                reservation_id = msg.get("reservationId")
                guest_name = msg.get("from")

                saved = save_message_from_webhook(
                    session=session,
                    message_id=message_id,
                    message_text=message_text,
                    timestamp=timestamp,
                    conversation_id=conversation_id,
                    reservation_id=reservation_id,
                    guest_name=guest_name,
                )

                if saved:
                    stats["new_saved"] += 1
                    logger.debug(f"Saved new message: {message_id}")
                else:
                    stats["duplicates_skipped"] += 1
                    logger.debug(f"Skipped duplicate: {message_id}")

            skip += limit

            if skip >= total_count:
                has_more = False

        logger.info(
            f"Backfill complete: {stats['total_fetched']} fetched, "
            f"{stats['new_saved']} new, {stats['duplicates_skipped']} duplicates"
        )
        return stats

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise
    finally:
        session.close()


def main() -> int:
    """Main entry point for backfill script."""
    parser = argparse.ArgumentParser(
        description="Backfill historical messages from Guesty API"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=config.BACKFILL_DAYS,
        help=f"Number of days to backfill (default: {config.BACKFILL_DAYS})",
    )

    args = parser.parse_args()

    try:
        logger.info(f"Starting backfill for {args.days} days")
        stats = backfill_messages(args.days)

        print("\n" + "=" * 50)
        print("BACKFILL COMPLETE")
        print("=" * 50)
        print(f"Total messages fetched: {stats['total_fetched']}")
        print(f"New messages saved:     {stats['new_saved']}")
        print(f"Duplicates skipped:     {stats['duplicates_skipped']}")
        print("=" * 50)
        print(
            "\nNote: Saved messages will be processed and classified "
            "by the worker automatically."
        )

        return 0

    except ValueError as e:
        logger.error(f"Invalid argument: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
