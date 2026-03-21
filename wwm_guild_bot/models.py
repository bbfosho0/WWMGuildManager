from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

ROLE_BUCKETS = ("tank", "healer", "dps")
SIGNUP_STATES = ("main", "bench", "tentative", "absence")
EVENT_STATUSES = ("draft", "open", "closed", "locked")
RECURRENCE_TYPES = ("once", "weekly", "every_n_weeks")


@dataclass(slots=True)
class UserProfile:
    discord_user_id: int
    character_name: str
    mastery: str
    role: str
    primary_weapon: str
    secondary_weapon: str
    path_guide: str
    sect_boost: Optional[str]
    inner_way_1_name: str
    inner_way_1_level: int
    inner_way_2_name: str
    inner_way_2_level: int
    inner_way_3_name: str
    inner_way_3_level: int
    inner_way_4_name: str
    inner_way_4_level: int
    build_link: Optional[str]
    notes: Optional[str]
    updated_at: Optional[datetime] = None


@dataclass(slots=True)
class Event:
    id: int
    title: str
    description: str
    starts_at: datetime
    closes_at: datetime
    tank_cap: int
    healer_cap: int
    dps_cap: int
    bench_cap: int
    allow_tentative: bool
    status: str
    signup_channel_id: int
    signup_message_id: Optional[int]
    recurring_template_id: Optional[int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(slots=True)
class RecurringTemplate:
    id: int
    title: str
    description: str
    channel_id: int
    timezone: str
    recurrence_type: str
    weekdays_csv: str
    interval_weeks: int
    start_date: str
    time_of_day: str
    signup_open_lead_minutes: int
    close_offset_minutes: int
    tank_cap: int
    healer_cap: int
    dps_cap: int
    bench_cap: int
    allow_tentative: bool
    end_after_occurrences: Optional[int]
    end_date: Optional[str]
    active: bool
    generated_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
