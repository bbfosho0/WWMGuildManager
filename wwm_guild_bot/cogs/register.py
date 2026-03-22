from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..embeds import build_profile_embed
from ..models import ROLE_BUCKETS
from ..utils import ValidationError, build_simple_embed, normalize_optional_text

INNER_WAYS = (
    "Adaptive Steel",
    "Art of Resistance",
    "Battle Anthem",
    "Bitter Seasons",
    "Blossom Barrage",
    "Breaking Point",
    "Divine Roulette",
    "Echoes of Oblivion",
    "Envigorated Warrior",
    "Esoteric Revival",
    "Evasive Charge",
    "Evening Snow",
    "Exquisite Scenery",
    "Fivefold Bleed",
    "Flying Gourds",
    "Fury Harvest",
    "Insightful Strike",
    "Light Anew",
    "Mending Loom",
    "Morale Chant",
    "Mountain's Might",
    "Phantom Rally",
    "Restoring Blossom",
    "Riptide Reflex",
    "Rock Solid",
    "Royal Remedy",
    "Sandswirl Tail",
    "Seasonal Edge",
    "Shadow Assault",
    "Song of Tang",
    "Star Reacher",
    "Steadfast Stance",
    "Sword Horizon",
    "Sword Morph",
    "Thunderous Bloom",
    "Towline Sweep",
    "Trapped Beast",
    "Vendetta",
    "Vital Leech",
    "Wildfire Spark",
    "Wind Beneath Wings",
    "Wolfchaser's Art",
)
WEAPONS = (
    "Everspring Umbrella",
    "Heavenquaker Spear",
    "Infernal Twinblades",
    "Inkwell Fan",
    "Mortal Rope Dart",
    "Nameless Spear",
    "Nameless Sword",
    "Vernal Umbrella",
    "Panacea Fan",
    "Soulshade Umbrella",
    "Stormbreaker Spear",
    "Strategic Sword",
    "Thundercry Blade",
    "Unfettered Rope Dart",
)
MARTIAL_ARTS_PATHS = (
    "Bellstrike - Splendor",
    "Bellstrike - Umbra",
    "Silkbind - Jade",
    "Silkbind - Deluge",
    "Stonesplit - Might",
    "Bamboocut - Wind",
    "Bamboocut - Dust",
)
TIER_CHOICES = [app_commands.Choice(name=f"Tier {tier}", value=tier) for tier in range(1, 7)]


def build_registration_payload(
    interaction: discord.Interaction,
    *,
    character_name: str,
    mastery: str,
    role: str,
    primary_weapon: str,
    secondary_weapon: str,
    martial_arts_path: str,
    sect_boost: str | None,
    inner_way_1_name: str,
    inner_way_1_tier: int,
    inner_way_2_name: str,
    inner_way_2_tier: int,
    inner_way_3_name: str,
    inner_way_3_tier: int,
    inner_way_4_name: str,
    inner_way_4_tier: int,
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
        "path_guide": martial_arts_path.strip(),
        "sect_boost": normalize_optional_text(sect_boost),
        "notes": normalize_optional_text(notes),
    }
    for index, (name, level) in enumerate(
        (
            (inner_way_1_name, inner_way_1_tier),
            (inner_way_2_name, inner_way_2_tier),
            (inner_way_3_name, inner_way_3_tier),
            (inner_way_4_name, inner_way_4_tier),
        ),
        start=1,
    ):
        if name not in INNER_WAYS:
            raise ValidationError(f"Inner Way {index} must be selected from the supported list.")
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
            "2. Weapons and Martial Arts Path are selected from built-in options.\n"
            "3. Inner Way names use type-to-search autocomplete and each tier is chosen from 1 to 6.\n"
            "4. Open event posts and click Tank, Healer, DPS, Bench, Tentative, or Absence.\n"
            "5. Use `/signup_status` to review your active signups.\n"
            "6. Use `/withdraw event_id:<id>` if you need to leave an event."
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
            "Choose a Martial Arts Path, weapon, and role from the provided lists.\n"
            "Inner Ways must be picked from autocomplete, and tiers only go from 1 to 6.\n"
            "Event IDs come from event embeds and event list output.\n"
            "Only officers and admins can use officer commands."
        ),
        inline=False,
    )
    return embed


async def inner_way_autocomplete(
    _interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    query = current.strip().lower()
    matches = [name for name in INNER_WAYS if query in name.lower()] if query else list(INNER_WAYS)
    return [app_commands.Choice(name=name, value=name) for name in matches[:25]]


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
        primary_weapon="Choose your primary weapon.",
        secondary_weapon="Choose your secondary weapon.",
        martial_arts_path="Choose your Martial Arts Path.",
        sect_boost="Optional sect boost details.",
        inner_way_1_name="Inner Way 1 name. Start typing to search.",
        inner_way_1_tier="Inner Way 1 tier.",
        inner_way_2_name="Inner Way 2 name. Start typing to search.",
        inner_way_2_tier="Inner Way 2 tier.",
        inner_way_3_name="Inner Way 3 name. Start typing to search.",
        inner_way_3_tier="Inner Way 3 tier.",
        inner_way_4_name="Inner Way 4 name. Start typing to search.",
        inner_way_4_tier="Inner Way 4 tier.",
        notes="Optional notes about your build.",
    )
    @app_commands.choices(
        role=[app_commands.Choice(name=value.upper(), value=value) for value in ROLE_BUCKETS],
        primary_weapon=[app_commands.Choice(name=value, value=value) for value in WEAPONS],
        secondary_weapon=[app_commands.Choice(name=value, value=value) for value in WEAPONS],
        martial_arts_path=[app_commands.Choice(name=value, value=value) for value in MARTIAL_ARTS_PATHS],
        inner_way_1_tier=TIER_CHOICES,
        inner_way_2_tier=TIER_CHOICES,
        inner_way_3_tier=TIER_CHOICES,
        inner_way_4_tier=TIER_CHOICES,
    )
    @app_commands.autocomplete(
        inner_way_1_name=inner_way_autocomplete,
        inner_way_2_name=inner_way_autocomplete,
        inner_way_3_name=inner_way_autocomplete,
        inner_way_4_name=inner_way_autocomplete,
    )
    async def register_character(
        self,
        interaction: discord.Interaction,
        character_name: str,
        mastery: str,
        role: app_commands.Choice[str],
        primary_weapon: app_commands.Choice[str],
        secondary_weapon: app_commands.Choice[str],
        martial_arts_path: app_commands.Choice[str],
        inner_way_1_name: str,
        inner_way_1_tier: app_commands.Choice[int],
        inner_way_2_name: str,
        inner_way_2_tier: app_commands.Choice[int],
        inner_way_3_name: str,
        inner_way_3_tier: app_commands.Choice[int],
        inner_way_4_name: str,
        inner_way_4_tier: app_commands.Choice[int],
        sect_boost: str | None = None,
        notes: str | None = None,
    ) -> None:
        payload = build_registration_payload(
            interaction,
            character_name=character_name,
            mastery=mastery,
            role=role.value,
            primary_weapon=primary_weapon.value,
            secondary_weapon=secondary_weapon.value,
            martial_arts_path=martial_arts_path.value,
            sect_boost=sect_boost,
            inner_way_1_name=inner_way_1_name,
            inner_way_1_tier=inner_way_1_tier.value,
            inner_way_2_name=inner_way_2_name,
            inner_way_2_tier=inner_way_2_tier.value,
            inner_way_3_name=inner_way_3_name,
            inner_way_3_tier=inner_way_3_tier.value,
            inner_way_4_name=inner_way_4_name,
            inner_way_4_tier=inner_way_4_tier.value,
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
