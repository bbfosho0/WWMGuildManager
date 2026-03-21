from __future__ import annotations

from collections import defaultdict

import discord

from .models import Event, RecurringTemplate, UserProfile
from .utils import format_weekdays, merge_embed_description, to_discord_timestamp, utc_now



def build_profile_embed(profile: UserProfile, user: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title=f"{profile.character_name} — WWM Build",
        description=f"Stored primary build for {user.mention}.",
        color=0x2ECC71,
        timestamp=utc_now(),
    )
    embed.add_field(name="Mastery", value=profile.mastery, inline=True)
    embed.add_field(name="Role", value=profile.role.upper(), inline=True)
    embed.add_field(
        name="Weapons",
        value=f"{profile.primary_weapon} / {profile.secondary_weapon}",
        inline=False,
    )
    embed.add_field(name="Path Guide", value=profile.path_guide, inline=False)
    embed.add_field(name="Sect Boost", value=profile.sect_boost or "-", inline=False)
    embed.add_field(
        name="Inner Ways",
        value=(
            f"1. {profile.inner_way_1_name} Lv.{profile.inner_way_1_level}\n"
            f"2. {profile.inner_way_2_name} Lv.{profile.inner_way_2_level}\n"
            f"3. {profile.inner_way_3_name} Lv.{profile.inner_way_3_level}\n"
            f"4. {profile.inner_way_4_name} Lv.{profile.inner_way_4_level}"
        ),
        inline=False,
    )
    embed.add_field(name="Build Link", value=profile.build_link or "-", inline=False)
    embed.add_field(name="Notes", value=profile.notes or "-", inline=False)
    return embed



def build_signup_embed(event: Event, signups: list, counts: dict[str, int]) -> discord.Embed:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in signups:
        label = f"<@{row['discord_user_id']}> — **{row['character_name']}** ({row['mastery']})"
        if row["signup_state"] == "main" and row["role_bucket"]:
            grouped[row["role_bucket"]].append(label)
        else:
            grouped[row["signup_state"]].append(label)

    embed = discord.Embed(
        title=f"{event.title}  •  Event #{event.id}",
        description=merge_embed_description(
            event.description,
            f"Starts: {to_discord_timestamp(event.starts_at)}",
            f"Closes: {to_discord_timestamp(event.closes_at)}",
            f"Status: **{event.status.upper()}**",
        ),
        color=0x5865F2,
        timestamp=utc_now(),
    )
    embed.add_field(
        name="Caps",
        value=(
            f"Tank {counts['tank']}/{event.tank_cap}\n"
            f"Healer {counts['healer']}/{event.healer_cap}\n"
            f"DPS {counts['dps']}/{event.dps_cap}\n"
            f"Bench {counts['bench']}/{event.bench_cap}\n"
            f"Tentative {'On' if event.allow_tentative else 'Off'}"
        ),
        inline=False,
    )
    embed.add_field(name="Tanks", value="\n".join(grouped["tank"]) or "-", inline=False)
    embed.add_field(name="Healers", value="\n".join(grouped["healer"]) or "-", inline=False)
    embed.add_field(name="DPS", value="\n".join(grouped["dps"]) or "-", inline=False)
    embed.add_field(name="Bench", value="\n".join(grouped["bench"]) or "-", inline=False)
    embed.add_field(name="Tentative", value="\n".join(grouped["tentative"]) or "-", inline=False)
    embed.add_field(name="Absence", value="\n".join(grouped["absence"]) or "-", inline=False)
    embed.set_footer(text="SQLite is the source of truth • Last updated")
    return embed



def build_event_list_embed(events: list[Event], templates: list[RecurringTemplate]) -> discord.Embed:
    embed = discord.Embed(
        title="WWM Event Overview",
        color=0xF1C40F,
        timestamp=utc_now(),
    )
    event_lines = [
        (
            f"**#{event.id}** {event.title} — {to_discord_timestamp(event.starts_at)} "
            f"({event.status})"
        )
        for event in events[:15]
    ]
    template_lines = []
    for template in templates[:15]:
        weekdays = format_weekdays(
            [int(part) for part in template.weekdays_csv.split(",") if part.strip()]
        )
        template_lines.append(
            f"**Template #{template.id}** {template.title} — {template.recurrence_type}, "
            f"days: {weekdays}, active: {template.active}"
        )
    embed.add_field(name="Upcoming Events", value="\n".join(event_lines) or "-", inline=False)
    embed.add_field(name="Recurring Templates", value="\n".join(template_lines) or "-", inline=False)
    return embed



def build_template_created_embed(template: RecurringTemplate) -> discord.Embed:
    weekdays = format_weekdays(
        [int(part) for part in template.weekdays_csv.split(",") if part.strip()]
    )
    embed = discord.Embed(
        title=f"Recurring Template #{template.id} Created",
        description=(
            f"{template.title}\n"
            f"Type: **{template.recurrence_type}**\n"
            f"Weekdays: **{weekdays}**\n"
            f"Timezone: **{template.timezone}**\n"
            f"Start time: **{template.time_of_day}**"
        ),
        color=0x9B59B6,
        timestamp=utc_now(),
    )
    return embed
