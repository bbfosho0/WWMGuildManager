from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..embeds import build_event_list_embed, build_template_created_embed
from ..models import RECURRENCE_TYPES
from ..utils import (
    ValidationError,
    build_simple_embed,
    get_timezone,
    parse_date_input,
    parse_datetime_input,
    parse_time_input,
    parse_weekdays_csv,
)


class EventsCog(commands.Cog):
    def __init__(self, bot: "WWMGuildBot"):
        self.bot = bot

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)
        embed = build_simple_embed("Event Error", str(original), color=0xE74C3C)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def ensure_officer(self, interaction: discord.Interaction) -> None:
        if not self.bot.member_is_officer(interaction.user):
            raise ValidationError("Only officers/admins can use this command.")

    @app_commands.command(name="event_create", description="Create a one-time event in draft status.")
    @app_commands.describe(
        title="Short event title.",
        starts_at="YYYY-MM-DD HH:MM in the default timezone.",
        closes_at="YYYY-MM-DD HH:MM in the default timezone.",
        tank_cap="Main tank slots.",
        healer_cap="Main healer slots.",
        dps_cap="Main DPS slots.",
        bench_cap="Bench slots.",
        allow_tentative="Allow tentative signups.",
        signup_channel="Channel that will receive the signup embed.",
        description="Optional event notes.",
    )
    async def event_create(
        self,
        interaction: discord.Interaction,
        title: str,
        starts_at: str,
        closes_at: str,
        tank_cap: int,
        healer_cap: int,
        dps_cap: int,
        bench_cap: int,
        allow_tentative: bool,
        signup_channel: discord.TextChannel,
        description: str = "",
    ) -> None:
        self.ensure_officer(interaction)
        starts = parse_datetime_input(starts_at, self.bot.config.default_timezone)
        closes = parse_datetime_input(closes_at, self.bot.config.default_timezone)
        if closes >= starts:
            raise ValidationError("closes_at must be earlier than starts_at.")
        event_id = self.bot.db.create_event(
            {
                "title": title.strip(),
                "description": description.strip(),
                "starts_at": starts,
                "closes_at": closes,
                "tank_cap": tank_cap,
                "healer_cap": healer_cap,
                "dps_cap": dps_cap,
                "bench_cap": bench_cap,
                "allow_tentative": allow_tentative,
                "status": "draft",
                "signup_channel_id": signup_channel.id,
            }
        )
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Event Created",
                f"Created draft event **#{event_id}**. Run `/event_post event_id:{event_id}` to post it.",
                color=0x2ECC71,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="event_post", description="Post or repost an event signup embed.")
    async def event_post(self, interaction: discord.Interaction, event_id: int) -> None:
        self.ensure_officer(interaction)
        message = await self.bot.post_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Event Posted",
                f"Event #{event_id} is now posted: {message.jump_url}",
                color=0x2ECC71,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="event_create_recurring", description="Create a recurring event template.")
    @app_commands.describe(
        title="Template title.",
        recurrence_type="once, weekly, or every_n_weeks.",
        start_date="YYYY-MM-DD anchor date.",
        time_of_day="HH:MM local time in the chosen timezone.",
        close_offset_hours="Hours before start when signup closes.",
        signup_channel="Channel to post generated events into.",
        weekdays="Comma-separated weekdays, e.g. mon,wed,sun.",
        interval_weeks="Used only for every_n_weeks.",
        signup_open_lead_hours="How many hours before start the event row should be created.",
        timezone="IANA timezone, e.g. UTC or America/New_York.",
        end_date="Optional YYYY-MM-DD last valid date.",
        end_after_occurrences="Optional maximum number of generated events.",
        description="Optional event notes.",
    )
    @app_commands.choices(
        recurrence_type=[app_commands.Choice(name=value, value=value) for value in RECURRENCE_TYPES]
    )
    async def event_create_recurring(
        self,
        interaction: discord.Interaction,
        title: str,
        recurrence_type: app_commands.Choice[str],
        start_date: str,
        time_of_day: str,
        close_offset_hours: int,
        tank_cap: int,
        healer_cap: int,
        dps_cap: int,
        bench_cap: int,
        allow_tentative: bool,
        signup_channel: discord.TextChannel,
        weekdays: str = "",
        interval_weeks: int = 1,
        signup_open_lead_hours: int = 0,
        timezone: str = "UTC",
        end_date: str | None = None,
        end_after_occurrences: int | None = None,
        description: str = "",
    ) -> None:
        self.ensure_officer(interaction)
        parsed_start_date = parse_date_input(start_date)
        parsed_time = parse_time_input(time_of_day)
        _ = parsed_start_date, parsed_time  # validated only
        get_timezone(timezone.strip())
        parsed_weekdays = parse_weekdays_csv(weekdays)
        if recurrence_type.value == "weekly" and not parsed_weekdays:
            raise ValidationError("Weekly templates need at least one weekday.")
        if close_offset_hours < 0 or signup_open_lead_hours < 0:
            raise ValidationError("Offset values must be zero or higher.")
        if recurrence_type.value == "every_n_weeks" and interval_weeks < 1:
            raise ValidationError("interval_weeks must be at least 1.")
        if recurrence_type.value == "once":
            parsed_weekdays = []
        if end_date:
            parsed_end_date = parse_date_input(end_date)
            if parsed_end_date < parsed_start_date:
                raise ValidationError("end_date cannot be earlier than start_date.")
        template_id = self.bot.db.create_template(
            {
                "title": title.strip(),
                "description": description.strip(),
                "channel_id": signup_channel.id,
                "timezone": timezone.strip(),
                "recurrence_type": recurrence_type.value,
                "weekdays_csv": ",".join(str(index) for index in parsed_weekdays),
                "interval_weeks": interval_weeks,
                "start_date": start_date,
                "time_of_day": time_of_day,
                "signup_open_lead_minutes": signup_open_lead_hours * 60,
                "close_offset_minutes": close_offset_hours * 60,
                "tank_cap": tank_cap,
                "healer_cap": healer_cap,
                "dps_cap": dps_cap,
                "bench_cap": bench_cap,
                "allow_tentative": allow_tentative,
                "end_after_occurrences": end_after_occurrences,
                "end_date": end_date,
                "active": True,
            }
        )
        template = self.bot.db.get_template(template_id)
        assert template is not None
        await self.bot.scheduler.sync_recurring_templates()
        await interaction.response.send_message(
            embed=build_template_created_embed(template),
            ephemeral=True,
        )

    @app_commands.command(name="event_list", description="List upcoming events and recurring templates.")
    async def event_list(self, interaction: discord.Interaction) -> None:
        self.ensure_officer(interaction)
        events = self.bot.db.list_upcoming_events()
        templates = self.bot.db.list_templates(active_only=False)
        await interaction.response.send_message(
            embed=build_event_list_embed(events, templates),
            ephemeral=True,
        )


async def setup(bot: "WWMGuildBot") -> None:
    cog = EventsCog(bot)
    await bot.add_cog(cog, guild=bot.guild_object)
