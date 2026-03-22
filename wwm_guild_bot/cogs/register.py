from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..embeds import build_profile_embed
from ..models import ROLE_BUCKETS
from ..utils import ValidationError, build_simple_embed, normalize_optional_text, parse_inner_way_pair


def build_registration_payload(
    interaction: discord.Interaction,
    *,
    character_name: str,
    mastery: str,
    role: str,
    primary_weapon: str,
    secondary_weapon: str,
    path_guide: str,
    sect_boost: str | None,
    inner_way_1: str,
    inner_way_2: str,
    inner_way_3: str,
    inner_way_4: str,
    notes: str | None,
) -> dict:
    role_value = role.strip().lower()
    if role_value not in ROLE_BUCKETS:
        raise ValidationError("Role must be tank, healer, or dps.")

    payload = {
        "discord_user_id": interaction.user.id,
        "character_name": character_name.strip(),
        "mastery": mastery.strip(),
        "role": role_value,
        "primary_weapon": primary_weapon.strip(),
        "secondary_weapon": secondary_weapon.strip(),
        "path_guide": path_guide.strip(),
        "sect_boost": normalize_optional_text(sect_boost),
        "notes": normalize_optional_text(notes),
    }
    for index, value in enumerate((inner_way_1, inner_way_2, inner_way_3, inner_way_4), start=1):
        name, level = parse_inner_way_pair(value)
        payload[f"inner_way_{index}_name"] = name
        payload[f"inner_way_{index}_level"] = level
    return payload


def build_help_embed() -> discord.Embed:
    embed = build_simple_embed(
        "WWM Guild Bot Help",
        "Use these commands and buttons to register your build, sign up for events, and manage rosters.",
        color=0x5865F2,
    )
    embed.add_field(
        name="Quick Start",
        value=(
            "1. Run `/register_character` and fill every field.\n"
            "2. Use `Inner Way` fields in `Name:Level` format, for example `Iron Bone:12`.\n"
            "3. Open event posts and click Tank, Healer, DPS, Bench, Tentative, or Absence.\n"
            "4. Use `/signup_status` to review your active signups.\n"
            "5. Use `/withdraw event_id:<id>` if you need to leave an event."
        ),
        inline=False,
    )
    embed.add_field(
        name="Member Commands",
        value=(
            "`/register_character` Register or update your single stored build.\n"
            "`/my_build` Review your saved build profile.\n"
            "`/signup_status` See every event you are signed up for.\n"
            "`/withdraw event_id:<id>` Remove yourself from one event."
        ),
        inline=False,
    )
    embed.add_field(
        name="Signup Buttons",
        value=(
            "`Tank`, `Healer`, `DPS` claim a main-role slot.\n"
            "`Bench` places you on the bench.\n"
            "`Tentative` marks you unsure if that event allows it.\n"
            "`Absence` marks that you cannot attend.\n"
            "`Withdraw` removes your signup.\n"
            "`Refresh` is officer-only and re-renders the event post."
        ),
        inline=False,
    )
    embed.add_field(
        name="Officer Commands",
        value=(
            "`/event_create` Create a one-time draft event.\n"
            "`/event_post` Post or repost the signup embed.\n"
            "`/event_create_recurring` Create a recurring template.\n"
            "`/event_list` Review upcoming events and templates.\n"
            "`/event_close`, `/event_lock`, `/event_unlock` control signup state.\n"
            "`/roster_move`, `/roster_remove`, `/event_refresh`, `/template_toggle` are officer maintenance tools."
        ),
        inline=False,
    )
    embed.add_field(
        name="Common Gotchas",
        value=(
            "You must register with `/register_character` before using signup buttons.\n"
            "If an inner way fails validation, use `Name:Level` with a whole-number level.\n"
            "Event IDs come from event embeds and event list output.\n"
            "Only officers and admins can use officer commands."
        ),
        inline=False,
    )
    return embed


class RegisterCog(commands.Cog):
    def __init__(self, bot: "WWMGuildBot"):
        self.bot = bot

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)
        description = str(original)
        await self._send_error(interaction, description)

    async def _send_error(self, interaction: discord.Interaction, description: str) -> None:
        embed = build_simple_embed("Registration Error", description, color=0xE74C3C)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Show how to use the WWM guild bot.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=build_help_embed(), ephemeral=True)

    @app_commands.command(name="register_character", description="Register or update your one WWM character/build.")
    @app_commands.describe(
        character_name="Your in-game character name.",
        mastery="Your character mastery.",
        role="Your signup role bucket.",
        primary_weapon="Your primary weapon.",
        secondary_weapon="Your secondary weapon.",
        path_guide="Your path guide.",
        sect_boost="Optional sect boost details.",
        inner_way_1="Inner Way 1 in Name:Level format.",
        inner_way_2="Inner Way 2 in Name:Level format.",
        inner_way_3="Inner Way 3 in Name:Level format.",
        inner_way_4="Inner Way 4 in Name:Level format.",
        notes="Optional notes about your build.",
    )
    @app_commands.choices(
        role=[app_commands.Choice(name=value.upper(), value=value) for value in ROLE_BUCKETS]
    )
    async def register_character(
        self,
        interaction: discord.Interaction,
        character_name: str,
        mastery: str,
        role: app_commands.Choice[str],
        primary_weapon: str,
        secondary_weapon: str,
        path_guide: str,
        inner_way_1: str,
        inner_way_2: str,
        inner_way_3: str,
        inner_way_4: str,
        sect_boost: str | None = None,
        notes: str | None = None,
    ) -> None:
        payload = build_registration_payload(
            interaction,
            character_name=character_name,
            mastery=mastery,
            role=role.value,
            primary_weapon=primary_weapon,
            secondary_weapon=secondary_weapon,
            path_guide=path_guide,
            sect_boost=sect_boost,
            inner_way_1=inner_way_1,
            inner_way_2=inner_way_2,
            inner_way_3=inner_way_3,
            inner_way_4=inner_way_4,
            notes=notes,
        )
        self.bot.db.upsert_user(payload)
        profile = self.bot.db.get_user(interaction.user.id)
        assert profile is not None
        await interaction.response.send_message(
            embed=build_profile_embed(profile, interaction.user),
            ephemeral=True,
        )

    @app_commands.command(name="my_build", description="Show your stored WWM build details.")
    async def my_build(self, interaction: discord.Interaction) -> None:
        profile = self.bot.db.get_user(interaction.user.id)
        if profile is None:
            raise ValidationError("You have not registered a build yet. Use /register_character.")
        await interaction.response.send_message(
            embed=build_profile_embed(profile, interaction.user),
            ephemeral=True,
        )

    @app_commands.command(name="signup_status", description="Show all of your current event signups.")
    async def signup_status(self, interaction: discord.Interaction) -> None:
        rows = self.bot.db.list_user_signups(interaction.user.id)
        if not rows:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "No Signups",
                    "You do not have any event signups right now.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )
            return
        lines = []
        for row in rows:
            position = row["role_bucket"].upper() if row["signup_state"] == "main" else row["signup_state"].title()
            lines.append(
                f"Event **#{row['event_id']}** {row['title']} - {position} - {row['status']}"
            )
        await interaction.response.send_message(
            embed=build_simple_embed("Your Signups", "\n".join(lines), color=0x5865F2),
            ephemeral=True,
        )

    @app_commands.command(name="withdraw", description="Withdraw yourself from an event.")
    @app_commands.describe(event_id="Numeric event ID shown in event lists or embeds.")
    async def withdraw(self, interaction: discord.Interaction, event_id: int) -> None:
        message = await self.bot.withdraw_signup(event_id, interaction.user.id)
        await interaction.response.send_message(
            embed=build_simple_embed("Withdrawn", message, color=0x2ECC71),
            ephemeral=True,
        )


async def setup(bot: "WWMGuildBot") -> None:
    cog = RegisterCog(bot)
    await bot.add_cog(cog, guild=bot.guild_object)
