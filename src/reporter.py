"""Report generation module for daily summaries and ad-hoc queries."""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from .config import config
from .database import Message, get_engine, get_session
from .guesty_client import GuestyClient
from .logger import logger


def generate_daily_summary(target_date: date | None = None) -> str:
    """
    Generate a daily summary report of arrivals and special requests.

    Args:
        target_date: Date to generate report for (defaults to today)

    Returns:
        Markdown-formatted summary report
    """
    if target_date is None:
        target_date = date.today()

    client = GuestyClient()
    engine = get_engine(config.DATABASE_URL)
    session = get_session(engine)

    try:
        logger.info(f"Generating daily summary for {target_date}")

        reservations = _get_arrivals_for_date(client, target_date)

        if not reservations:
            return f"📅 **Daily Summary ({target_date.strftime('%B %d, %Y')})**\n\n" \
                   f"No arrivals scheduled for today."

        report_lines = [
            f"📅 **Daily Summary ({target_date.strftime('%B %d, %Y')})**\n"
        ]

        for reservation in reservations:
            reservation_id = reservation.get("_id", "N/A")
            guest = reservation.get("guest", {})
            guest_name = (
                guest.get("fullName")
                or f"{guest.get('firstName', '')} {guest.get('lastName', '')}".strip()
                or "Unknown Guest"
            )

            listing = reservation.get("listing", {})
            property_name = (
                listing.get("title")
                or listing.get("nickname")
                or listing.get("address", {}).get("full")
                or "Unknown Property"
            )

            # checkin_date = reservation.get("checkIn")
            # checkout_date = reservation.get("checkOut")
            nights = reservation.get("nightsCount", "?")

            messages = _get_messages_for_reservation(session, reservation_id)

            report_lines.append(f"\n- **{guest_name}** (Arrives today @ {property_name})")

            special_requests = [
                msg for msg in messages
                if msg.llm_category in ["EARLY_CHECKIN", "LATE_CHECKOUT", "SPECIAL_REQUEST"]
            ]

            if special_requests:
                for msg in special_requests:
                    category_label = (
                        msg.llm_category.replace("_", " ").title()
                        if msg.llm_category
                        else "Request"
                    )
                    report_lines.append(f"  - {category_label}: {msg.llm_summary}")
            else:
                report_lines.append("  - No special requests noted")

            report_lines.append(f"  - {reservation.get('guestsCount', '?')} guests, " \
                              f"{nights} nights")

        return "\n".join(report_lines)

    except Exception as e:
        logger.error(f"Failed to generate daily summary: {e}")
        raise
    finally:
        session.close()


def _get_arrivals_for_date(
    client: GuestyClient, target_date: date
) -> list[dict[str, Any]]:
    """
    Fetch reservations arriving on the specified date from Guesty API.

    Args:
        client: GuestyClient instance
        target_date: Date to filter by

    Returns:
        List of reservation objects
    """
    checkin_start = datetime.combine(
        target_date, datetime.min.time()
    ).replace(tzinfo=UTC)
    checkin_end = checkin_start + timedelta(days=1)

    logger.info(f"Fetching reservations for {target_date}")

    response = client.get_reservations(
        checkin_from=checkin_start.isoformat(),
        checkin_to=checkin_end.isoformat(),
        limit=100,
    )
    results: list[dict[str, Any]] = response.get("results", [])

    logger.info(f"Found {len(results)} reservations for {target_date}")
    return results


def _get_messages_for_reservation(
    session: Session, reservation_id: str
) -> list[Message]:
    """
    Fetch classified messages for a specific reservation from the database.

    Args:
        session: SQLAlchemy Session instance
        reservation_id: Guesty reservation ID

    Returns:
        List of Message objects with classification data
    """
    stmt = select(Message).where(
        and_(
            Message.reservation_id == reservation_id,
            Message.is_processed.is_(True),
            Message.llm_category.isnot(None)
        )
    ).order_by(Message.timestamp.asc())

    result = session.execute(stmt)
    return list(result.scalars().all())
