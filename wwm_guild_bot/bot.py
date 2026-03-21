from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord
from discord.ext import commands

from .config import Config, ConfigError, load_config
from .db import Database
from .embeds import build_signup_embed
from .scheduler import BotScheduler
from .utils import ValidationError
from .views import SignupView

LOGGER = logging.getLogger("wwm_guild_bot")


class WWMGuildBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self.db = Database(config.sqlite_path)
        self.scheduler = BotScheduler(self)
        self.registration_sessions: dict[int, dict[str, Any]] = {}
        self.guild_object = discord.Object(id=config.discord_guild_id)

    async def setup_hook(self) -> None:
        self.db.init_db()
        await self.load_extension("wwm_guild_bot.cogs.register")
        await self.load_extension("wwm_guild_bot.cogs.events")
        await self.load_extension("wwm_guild_bot.cogs.admin")
        await self.tree.sync(guild=self.guild_object)
        self.restore_persistent_views()
        self.scheduler.start()

    async def close(self) -> None:
        self.scheduler.shutdown()
        await super().close()

    def restore_persistent_views(self) -> None:
        for event in self.db.list_events_with_messages():
            if event.signup_message_id is None:
                continue
            self.add_view(SignupView(self, event.id), message_id=event.signup_message_id)

    def member_is_officer(self, user: discord.abc.User) -> bool:
        if not isinstance(user, discord.Member):
            return False
        if user.guild_permissions.administrator:
            return True
        allowed = {name.lower() for name in (*self.config.officer_role_names, *self.config.admin_role_names)}
        return any(role.name.lower() in allowed for role in user.roles)

    async def ensure_signup_allowed(
        self,
        event_id: int,
        user: discord.abc.User,
        officer_override: bool = False,
    ):
        profile = self.db.get_user(user.id)
        if profile is None:
            raise ValidationError("You need to register your character first with /register_character.")
        event = self.db.get_event(event_id)
        if event is None:
            raise ValidationError(f"Event #{event_id} does not exist.")
        if event.status == "locked" and not officer_override:
            raise ValidationError("This event is locked. Ask an officer if changes are needed.")
        if event.status == "closed" and not officer_override:
            raise ValidationError("This event is closed. Ask an officer for an override.")
        if event.status == "draft" and not officer_override:
            raise ValidationError("This event has not been posted yet.")
        return event, profile

    async def handle_signup_action(self, event_id: int, user: discord.abc.User, action: str) -> str:
        event, _profile = await self.ensure_signup_allowed(event_id, user)

        if action in {"tank", "healer", "dps"}:
            cap_lookup = {
                "tank": event.tank_cap,
                "healer": event.healer_cap,
                "dps": event.dps_cap,
            }
            current = self.db.count_main_role(event_id, action)
            existing = self.db.get_signup(event_id, user.id)
            already_in_same_bucket = (
                existing is not None
                and existing["signup_state"] == "main"
                and existing["role_bucket"] == action
            )
            if current >= cap_lookup[action] and not already_in_same_bucket:
                raise ValidationError(f"{action.title()} cap is full for this event.")
            self.db.upsert_signup(event_id, user.id, "main", action)
            await self.refresh_event_message(event_id)
            return f"You are signed up as **{action.upper()}** for event #{event_id}."

        if action == "bench":
            current = self.db.count_state(event_id, "bench")
            existing = self.db.get_signup(event_id, user.id)
            already_bench = existing is not None and existing["signup_state"] == "bench"
            if current >= event.bench_cap and not already_bench:
                raise ValidationError("Bench cap is full for this event.")
            self.db.upsert_signup(event_id, user.id, "bench", None)
            await self.refresh_event_message(event_id)
            return f"You are on the **bench** for event #{event_id}."

        if action == "tentative":
            if not event.allow_tentative:
                raise ValidationError("Tentative signups are disabled for this event.")
            self.db.upsert_signup(event_id, user.id, "tentative", None)
            await self.refresh_event_message(event_id)
            return f"You are marked **tentative** for event #{event_id}."

        if action == "absence":
            self.db.upsert_signup(event_id, user.id, "absence", None)
            await self.refresh_event_message(event_id)
            return f"You are marked **absent** for event #{event_id}."

        raise ValidationError(f"Unknown signup action: {action}")

    async def withdraw_signup(self, event_id: int, user_id: int) -> str:
        event = self.db.get_event(event_id)
        if event is None:
            raise ValidationError(f"Event #{event_id} does not exist.")
        signup = self.db.get_signup(event_id, user_id)
        if signup is None:
            raise ValidationError("You do not have a signup for that event.")
        self.db.delete_signup(event_id, user_id)
        await self.refresh_event_message(event_id)
        return f"Your signup was removed from event #{event_id}."

    async def post_event_message(self, event_id: int, *, open_if_draft: bool = True) -> discord.Message:
        event = self.db.get_event(event_id)
        if event is None:
            raise ValidationError(f"Event #{event_id} does not exist.")
        if event.status == "draft" and open_if_draft:
            self.db.update_event_status(event_id, "open")
            event = self.db.get_event(event_id)
            assert event is not None

        channel = self.get_channel(event.signup_channel_id)
        if channel is None:
            channel = await self.fetch_channel(event.signup_channel_id)
        if not hasattr(channel, "send"):
            raise ValidationError("Configured signup channel is not messageable.")

        signups = self.db.list_signups_for_event(event_id)
        counts = self.db.get_signup_counts(event_id)
        embed = build_signup_embed(event, signups, counts)
        view = SignupView(self, event_id)
        message = await channel.send(embed=embed, view=view)
        self.db.update_event_message(event_id, event.signup_channel_id, message.id)
        self.add_view(view, message_id=message.id)
        return message

    async def refresh_event_message(self, event_id: int) -> None:
        event = self.db.get_event(event_id)
        if event is None:
            raise ValidationError(f"Event #{event_id} does not exist.")
        if event.signup_message_id is None:
            await self.post_event_message(event_id, open_if_draft=False)
            return

        signups = self.db.list_signups_for_event(event_id)
        counts = self.db.get_signup_counts(event_id)
        embed = build_signup_embed(event, signups, counts)
        view = SignupView(self, event_id)

        try:
            channel = self.get_channel(event.signup_channel_id)
            if channel is None:
                channel = await self.fetch_channel(event.signup_channel_id)
            message = await channel.fetch_message(event.signup_message_id)
            await message.edit(embed=embed, view=view)
            self.add_view(view, message_id=event.signup_message_id)
        except discord.NotFound:
            LOGGER.warning("Signup message missing for event %s. Reposting.", event_id)
            self.db.update_event_message(event_id, event.signup_channel_id, None)
            await self.post_event_message(event_id, open_if_draft=False)


async def run_bot() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        config = load_config()
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc

    bot = WWMGuildBot(config)
    async with bot:
        await bot.start(config.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(run_bot())
