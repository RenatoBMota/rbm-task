from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("America/Sao_Paulo")


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)
