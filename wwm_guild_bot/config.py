from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    discord_bot_token: str
    discord_guild_id: int
    sqlite_path: str
    default_timezone: str
    officer_role_names: tuple[str, ...]
    admin_role_names: tuple[str, ...]


class ConfigError(RuntimeError):
    pass



def _parse_role_names(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())



def load_config() -> Config:
    load_dotenv()

    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    sqlite_path = os.getenv("SQLITE_PATH", "wwm_guild_bot.sqlite3").strip()
    default_timezone = os.getenv("DEFAULT_TIMEZONE", "UTC").strip() or "UTC"
    officer_role_names = _parse_role_names(os.getenv("OFFICER_ROLE_NAMES", "Officer"))
    admin_role_names = _parse_role_names(os.getenv("ADMIN_ROLE_NAMES", "Admin"))

    if not token:
        raise ConfigError("DISCORD_BOT_TOKEN is required.")
    if not guild_id_raw:
        raise ConfigError("DISCORD_GUILD_ID is required for this single-server MVP.")

    try:
        guild_id = int(guild_id_raw)
    except ValueError as exc:
        raise ConfigError("DISCORD_GUILD_ID must be an integer.") from exc

    return Config(
        discord_bot_token=token,
        discord_guild_id=guild_id,
        sqlite_path=sqlite_path,
        default_timezone=default_timezone,
        officer_role_names=officer_role_names,
        admin_role_names=admin_role_names,
    )
