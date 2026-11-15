"""时间工具：数据库统一存 UTC（naive），出口统一 +08:00 ISO8601。"""
from datetime import date, datetime, timedelta, timezone

from app.config import settings

TZ = timezone(timedelta(hours=8))


def utcnow() -> datetime:
    """naive UTC，写入数据库用。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now() -> datetime:
    return datetime.now(TZ)


def local_today() -> date:
    return local_now().date()


def iso(dt: datetime | None, *, with_tz: bool = True) -> str | None:
    if dt is None:
        return None
    aware = dt.replace(tzinfo=timezone.utc).astimezone(TZ) if dt.tzinfo is None else dt.astimezone(TZ)
    return aware.isoformat() if with_tz else aware.strftime("%Y-%m-%d %H:%M:%S")


def human_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(TZ).strftime("%m-%d %H:%M")


def local_date_str(d: date | None) -> str | None:
    return d.strftime("%Y-%m-%d") if d else None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def week_start_of(d: date) -> date:
    """周一为一周起点。"""
    return d - timedelta(days=d.weekday())


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)


def days_until(d: date) -> int:
    return (d - local_today()).days


def now_naive_from_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


GREETINGS = ((11, "上午好"), (14, "中午好"), (18, "下午好"), (24, "晚上好"))


def greeting() -> str:
    h = local_now().hour
    for upper, text in GREETINGS:
        if h < upper:
            return text
    return "晚上好"


def current_week_no(d: date | None = None) -> int:
    d = d or local_today()
    return d.isocalendar().week


__all__ = [
    "TZ",
    "utcnow",
    "local_now",
    "local_today",
    "iso",
    "human_dt",
    "local_date_str",
    "parse_date",
    "week_start_of",
    "add_days",
    "days_until",
    "now_naive_from_iso",
    "greeting",
    "current_week_no",
    "settings",
]
