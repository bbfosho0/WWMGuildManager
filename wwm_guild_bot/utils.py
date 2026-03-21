from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from discord import Embed

WEEKDAY_NAME_TO_INDEX = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}
INDEX_TO_WEEKDAY_NAME = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


class ValidationError(ValueError):
    pass



def get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:  # pragma: no cover - ZoneInfo has platform-specific errors
        raise ValidationError(f"Unknown timezone: {name}") from exc



def parse_datetime_input(value: str, timezone_name: str) -> datetime:
    cleaned = value.strip()
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]
    for fmt in formats:
        try:
            naive = datetime.strptime(cleaned, fmt)
            return naive.replace(tzinfo=get_timezone(timezone_name))
        except ValueError:
            continue
    raise ValidationError("Datetime must be in YYYY-MM-DD HH:MM format.")



def parse_date_input(value: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("Date must be in YYYY-MM-DD format.") from exc



def parse_time_input(value: str) -> time:
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError as exc:
        raise ValidationError("Time must be in HH:MM 24-hour format.") from exc



def parse_weekdays_csv(value: str) -> list[int]:
    if not value.strip():
        return []
    indexes: list[int] = []
    for part in value.split(","):
        lookup = WEEKDAY_NAME_TO_INDEX.get(part.strip().lower())
        if lookup is None:
            raise ValidationError(
                f"Invalid weekday '{part.strip()}'. Use names like mon, wed, sun."
            )
        if lookup not in indexes:
            indexes.append(lookup)
    return sorted(indexes)



def format_weekdays(indexes: list[int]) -> str:
    if not indexes:
        return "-"
    return ", ".join(INDEX_TO_WEEKDAY_NAME[index] for index in sorted(indexes))



def utc_now() -> datetime:
    return datetime.now(tz=ZoneInfo("UTC"))



def to_storage_datetime(value: datetime) -> str:
    return value.astimezone(ZoneInfo("UTC")).isoformat()



def from_storage_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(ZoneInfo("UTC"))



def to_discord_timestamp(value: datetime, style: str = "f") -> str:
    return f"<t:{int(value.timestamp())}:{style}>"



def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None



def parse_inner_way_pair(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise ValidationError("Inner way must use Name:Level format, e.g. Iron Bone:12.")
    name, level_raw = value.split(":", 1)
    name = name.strip()
    if not name:
        raise ValidationError("Inner way name cannot be empty.")
    try:
        level = int(level_raw.strip())
    except ValueError as exc:
        raise ValidationError("Inner way level must be a whole number.") from exc
    if level < 0:
        raise ValidationError("Inner way level must be zero or higher.")
    return name, level



def merge_embed_description(*parts: str) -> str:
    return "\n".join(part for part in parts if part)



def localize_event_time(start_date: date, time_of_day: time, timezone_name: str) -> datetime:
    return datetime.combine(start_date, time_of_day, tzinfo=get_timezone(timezone_name))



def apply_close_offset(starts_at: datetime, close_offset_minutes: int) -> datetime:
    return starts_at - timedelta(minutes=close_offset_minutes)



def build_simple_embed(title: str, description: str, *, color: int = 0x5865F2) -> Embed:
    return Embed(title=title, description=description, color=color)
