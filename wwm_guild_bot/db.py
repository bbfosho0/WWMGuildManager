from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from .models import Event, RecurringTemplate, UserProfile
from .utils import from_storage_datetime, to_storage_datetime, utc_now


class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    discord_user_id INTEGER PRIMARY KEY,
                    character_name TEXT NOT NULL,
                    mastery TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('tank', 'healer', 'dps')),
                    primary_weapon TEXT NOT NULL,
                    secondary_weapon TEXT NOT NULL,
                    path_guide TEXT NOT NULL,
                    sect_boost TEXT,
                    inner_way_1_name TEXT NOT NULL,
                    inner_way_1_level INTEGER NOT NULL,
                    inner_way_2_name TEXT NOT NULL,
                    inner_way_2_level INTEGER NOT NULL,
                    inner_way_3_name TEXT NOT NULL,
                    inner_way_3_level INTEGER NOT NULL,
                    inner_way_4_name TEXT NOT NULL,
                    inner_way_4_level INTEGER NOT NULL,
                    build_link TEXT,
                    notes TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS recurring_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    timezone TEXT NOT NULL,
                    recurrence_type TEXT NOT NULL CHECK(recurrence_type IN ('once', 'weekly', 'every_n_weeks')),
                    weekdays_csv TEXT NOT NULL DEFAULT '',
                    interval_weeks INTEGER NOT NULL DEFAULT 1,
                    start_date TEXT NOT NULL,
                    time_of_day TEXT NOT NULL,
                    signup_open_lead_minutes INTEGER NOT NULL DEFAULT 0,
                    close_offset_minutes INTEGER NOT NULL,
                    tank_cap INTEGER NOT NULL,
                    healer_cap INTEGER NOT NULL,
                    dps_cap INTEGER NOT NULL,
                    bench_cap INTEGER NOT NULL,
                    allow_tentative INTEGER NOT NULL DEFAULT 1,
                    end_after_occurrences INTEGER,
                    end_date TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    generated_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    closes_at TEXT NOT NULL,
                    tank_cap INTEGER NOT NULL,
                    healer_cap INTEGER NOT NULL,
                    dps_cap INTEGER NOT NULL,
                    bench_cap INTEGER NOT NULL,
                    allow_tentative INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL CHECK(status IN ('draft', 'open', 'closed', 'locked')),
                    signup_channel_id INTEGER NOT NULL,
                    signup_message_id INTEGER,
                    recurring_template_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(recurring_template_id) REFERENCES recurring_templates(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS signups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    discord_user_id INTEGER NOT NULL,
                    signup_state TEXT NOT NULL CHECK(signup_state IN ('main', 'bench', 'tentative', 'absence')),
                    role_bucket TEXT CHECK(role_bucket IN ('tank', 'healer', 'dps')),
                    updated_at TEXT NOT NULL,
                    UNIQUE(event_id, discord_user_id),
                    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
                    FOREIGN KEY(discord_user_id) REFERENCES users(discord_user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_events_starts_at ON events(starts_at);
                CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
                CREATE INDEX IF NOT EXISTS idx_signups_event_id ON signups(event_id);
                CREATE INDEX IF NOT EXISTS idx_templates_active ON recurring_templates(active);
                """
            )

    def _row_to_user(self, row: sqlite3.Row | None) -> UserProfile | None:
        if row is None:
            return None
        return UserProfile(
            discord_user_id=row["discord_user_id"],
            character_name=row["character_name"],
            mastery=row["mastery"],
            role=row["role"],
            primary_weapon=row["primary_weapon"],
            secondary_weapon=row["secondary_weapon"],
            path_guide=row["path_guide"],
            sect_boost=row["sect_boost"],
            inner_way_1_name=row["inner_way_1_name"],
            inner_way_1_level=row["inner_way_1_level"],
            inner_way_2_name=row["inner_way_2_name"],
            inner_way_2_level=row["inner_way_2_level"],
            inner_way_3_name=row["inner_way_3_name"],
            inner_way_3_level=row["inner_way_3_level"],
            inner_way_4_name=row["inner_way_4_name"],
            inner_way_4_level=row["inner_way_4_level"],
            build_link=row["build_link"],
            notes=row["notes"],
            updated_at=from_storage_datetime(row["updated_at"]),
        )

    def _row_to_event(self, row: sqlite3.Row | None) -> Event | None:
        if row is None:
            return None
        return Event(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            starts_at=from_storage_datetime(row["starts_at"]),
            closes_at=from_storage_datetime(row["closes_at"]),
            tank_cap=row["tank_cap"],
            healer_cap=row["healer_cap"],
            dps_cap=row["dps_cap"],
            bench_cap=row["bench_cap"],
            allow_tentative=bool(row["allow_tentative"]),
            status=row["status"],
            signup_channel_id=row["signup_channel_id"],
            signup_message_id=row["signup_message_id"],
            recurring_template_id=row["recurring_template_id"],
            created_at=from_storage_datetime(row["created_at"]),
            updated_at=from_storage_datetime(row["updated_at"]),
        )

    def _row_to_template(self, row: sqlite3.Row | None) -> RecurringTemplate | None:
        if row is None:
            return None
        return RecurringTemplate(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            channel_id=row["channel_id"],
            timezone=row["timezone"],
            recurrence_type=row["recurrence_type"],
            weekdays_csv=row["weekdays_csv"],
            interval_weeks=row["interval_weeks"],
            start_date=row["start_date"],
            time_of_day=row["time_of_day"],
            signup_open_lead_minutes=row["signup_open_lead_minutes"],
            close_offset_minutes=row["close_offset_minutes"],
            tank_cap=row["tank_cap"],
            healer_cap=row["healer_cap"],
            dps_cap=row["dps_cap"],
            bench_cap=row["bench_cap"],
            allow_tentative=bool(row["allow_tentative"]),
            end_after_occurrences=row["end_after_occurrences"],
            end_date=row["end_date"],
            active=bool(row["active"]),
            generated_count=row["generated_count"],
            created_at=from_storage_datetime(row["created_at"]),
            updated_at=from_storage_datetime(row["updated_at"]),
        )

    def upsert_user(self, payload: dict[str, Any]) -> None:
        now = to_storage_datetime(utc_now())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    discord_user_id, character_name, mastery, role, primary_weapon,
                    secondary_weapon, path_guide, sect_boost, inner_way_1_name,
                    inner_way_1_level, inner_way_2_name, inner_way_2_level,
                    inner_way_3_name, inner_way_3_level, inner_way_4_name,
                    inner_way_4_level, build_link, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    character_name=excluded.character_name,
                    mastery=excluded.mastery,
                    role=excluded.role,
                    primary_weapon=excluded.primary_weapon,
                    secondary_weapon=excluded.secondary_weapon,
                    path_guide=excluded.path_guide,
                    sect_boost=excluded.sect_boost,
                    inner_way_1_name=excluded.inner_way_1_name,
                    inner_way_1_level=excluded.inner_way_1_level,
                    inner_way_2_name=excluded.inner_way_2_name,
                    inner_way_2_level=excluded.inner_way_2_level,
                    inner_way_3_name=excluded.inner_way_3_name,
                    inner_way_3_level=excluded.inner_way_3_level,
                    inner_way_4_name=excluded.inner_way_4_name,
                    inner_way_4_level=excluded.inner_way_4_level,
                    build_link=excluded.build_link,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    payload["discord_user_id"],
                    payload["character_name"],
                    payload["mastery"],
                    payload["role"],
                    payload["primary_weapon"],
                    payload["secondary_weapon"],
                    payload["path_guide"],
                    payload.get("sect_boost"),
                    payload["inner_way_1_name"],
                    payload["inner_way_1_level"],
                    payload["inner_way_2_name"],
                    payload["inner_way_2_level"],
                    payload["inner_way_3_name"],
                    payload["inner_way_3_level"],
                    payload["inner_way_4_name"],
                    payload["inner_way_4_level"],
                    payload.get("build_link"),
                    payload.get("notes"),
                    now,
                ),
            )

    def get_user(self, discord_user_id: int) -> UserProfile | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()
        return self._row_to_user(row)

    def create_event(self, payload: dict[str, Any]) -> int:
        now = to_storage_datetime(utc_now())
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    title, description, starts_at, closes_at, tank_cap, healer_cap,
                    dps_cap, bench_cap, allow_tentative, status, signup_channel_id,
                    signup_message_id, recurring_template_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload.get("description", ""),
                    to_storage_datetime(payload["starts_at"]),
                    to_storage_datetime(payload["closes_at"]),
                    payload["tank_cap"],
                    payload["healer_cap"],
                    payload["dps_cap"],
                    payload["bench_cap"],
                    1 if payload["allow_tentative"] else 0,
                    payload["status"],
                    payload["signup_channel_id"],
                    payload.get("signup_message_id"),
                    payload.get("recurring_template_id"),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_event_status(self, event_id: int, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE events SET status = ?, updated_at = ? WHERE id = ?",
                (status, to_storage_datetime(utc_now()), event_id),
            )

    def update_event_message(self, event_id: int, channel_id: int, message_id: int | None) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE events
                SET signup_channel_id = ?, signup_message_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (channel_id, message_id, to_storage_datetime(utc_now()), event_id),
            )

    def get_event(self, event_id: int) -> Event | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return self._row_to_event(row)

    def list_events(self, *, include_closed: bool = True) -> list[Event]:
        query = "SELECT * FROM events"
        params: tuple[Any, ...] = ()
        if not include_closed:
            query += " WHERE status IN ('draft', 'open', 'locked')"
        query += " ORDER BY starts_at ASC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_event(row) for row in rows if row is not None]

    def list_upcoming_events(self) -> list[Event]:
        now = to_storage_datetime(utc_now())
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE starts_at >= ? ORDER BY starts_at ASC",
                (now,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows if row is not None]

    def list_events_with_messages(self) -> list[Event]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE signup_message_id IS NOT NULL
                ORDER BY starts_at ASC
                """
            ).fetchall()
        return [self._row_to_event(row) for row in rows if row is not None]

    def get_expired_open_event_ids(self) -> list[int]:
        now = to_storage_datetime(utc_now())
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id FROM events WHERE status = 'open' AND closes_at <= ?",
                (now,),
            ).fetchall()
        return [int(row["id"]) for row in rows]

    def list_user_signups(self, discord_user_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.event_id, s.signup_state, s.role_bucket, e.title, e.starts_at, e.status
                FROM signups s
                JOIN events e ON e.id = s.event_id
                WHERE s.discord_user_id = ?
                ORDER BY e.starts_at ASC
                """,
                (discord_user_id,),
            ).fetchall()
        return rows

    def get_signup(self, event_id: int, discord_user_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM signups WHERE event_id = ? AND discord_user_id = ?",
                (event_id, discord_user_id),
            ).fetchone()

    def count_main_role(self, event_id: int, role_bucket: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM signups
                WHERE event_id = ? AND signup_state = 'main' AND role_bucket = ?
                """,
                (event_id, role_bucket),
            ).fetchone()
        return int(row["count"])

    def count_state(self, event_id: int, signup_state: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM signups WHERE event_id = ? AND signup_state = ?",
                (event_id, signup_state),
            ).fetchone()
        return int(row["count"])

    def upsert_signup(
        self,
        event_id: int,
        discord_user_id: int,
        signup_state: str,
        role_bucket: str | None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO signups (event_id, discord_user_id, signup_state, role_bucket, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(event_id, discord_user_id) DO UPDATE SET
                    signup_state=excluded.signup_state,
                    role_bucket=excluded.role_bucket,
                    updated_at=excluded.updated_at
                """,
                (
                    event_id,
                    discord_user_id,
                    signup_state,
                    role_bucket,
                    to_storage_datetime(utc_now()),
                ),
            )

    def delete_signup(self, event_id: int, discord_user_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM signups WHERE event_id = ? AND discord_user_id = ?",
                (event_id, discord_user_id),
            )

    def list_signups_for_event(self, event_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.discord_user_id,
                    s.signup_state,
                    s.role_bucket,
                    s.updated_at,
                    u.character_name,
                    u.mastery,
                    u.role AS registered_role
                FROM signups s
                JOIN users u ON u.discord_user_id = s.discord_user_id
                WHERE s.event_id = ?
                ORDER BY u.character_name COLLATE NOCASE ASC
                """,
                (event_id,),
            ).fetchall()
        return rows

    def create_template(self, payload: dict[str, Any]) -> int:
        now = to_storage_datetime(utc_now())
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO recurring_templates (
                    title, description, channel_id, timezone, recurrence_type, weekdays_csv,
                    interval_weeks, start_date, time_of_day, signup_open_lead_minutes,
                    close_offset_minutes, tank_cap, healer_cap, dps_cap, bench_cap,
                    allow_tentative, end_after_occurrences, end_date, active,
                    generated_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload.get("description", ""),
                    payload["channel_id"],
                    payload["timezone"],
                    payload["recurrence_type"],
                    payload.get("weekdays_csv", ""),
                    payload.get("interval_weeks", 1),
                    payload["start_date"],
                    payload["time_of_day"],
                    payload.get("signup_open_lead_minutes", 0),
                    payload["close_offset_minutes"],
                    payload["tank_cap"],
                    payload["healer_cap"],
                    payload["dps_cap"],
                    payload["bench_cap"],
                    1 if payload["allow_tentative"] else 0,
                    payload.get("end_after_occurrences"),
                    payload.get("end_date"),
                    1 if payload.get("active", True) else 0,
                    0,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_templates(self, *, active_only: bool = False) -> list[RecurringTemplate]:
        query = "SELECT * FROM recurring_templates"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY id ASC"
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return [self._row_to_template(row) for row in rows if row is not None]

    def get_template(self, template_id: int) -> RecurringTemplate | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM recurring_templates WHERE id = ?",
                (template_id,),
            ).fetchone()
        return self._row_to_template(row)

    def set_template_active(self, template_id: int, active: bool) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE recurring_templates SET active = ?, updated_at = ? WHERE id = ?",
                (1 if active else 0, to_storage_datetime(utc_now()), template_id),
            )

    def increment_template_generated_count(self, template_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE recurring_templates
                SET generated_count = generated_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (to_storage_datetime(utc_now()), template_id),
            )

    def template_has_event_at(self, template_id: int, starts_at: datetime) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM events
                WHERE recurring_template_id = ? AND starts_at = ?
                LIMIT 1
                """,
                (template_id, to_storage_datetime(starts_at)),
            ).fetchone()
        return row is not None

    def get_signup_counts(self, event_id: int) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT signup_state, role_bucket, COUNT(*) AS count
                FROM signups
                WHERE event_id = ?
                GROUP BY signup_state, role_bucket
                """,
                (event_id,),
            ).fetchall()
        counts = {
            "tank": 0,
            "healer": 0,
            "dps": 0,
            "bench": 0,
            "tentative": 0,
            "absence": 0,
        }
        for row in rows:
            if row["signup_state"] == "main" and row["role_bucket"]:
                counts[row["role_bucket"]] = int(row["count"])
            else:
                counts[row["signup_state"]] = int(row["count"])
        return counts
