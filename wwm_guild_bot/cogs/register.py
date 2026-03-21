from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..embeds import build_profile_embed
from ..models import ROLE_BUCKETS
from ..utils import ValidationError, build_simple_embed, normalize_optional_text, parse_inner_way_pair


def profile_to_payload(profile) -> dict:
    return {
        "character_name": profile.character_name,
        "mastery": profile.mastery,
        "role": profile.role,
        "primary_weapon": profile.primary_weapon,
        "secondary_weapon": profile.secondary_weapon,
        "path_guide": profile.path_guide,
        "sect_boost": profile.sect_boost,
        "inner_way_1_name": profile.inner_way_1_name,
        "inner_way_1_level": profile.inner_way_1_level,
        "inner_way_2_name": profile.inner_way_2_name,
        "inner_way_2_level": profile.inner_way_2_level,
        "inner_way_3_name": profile.inner_way_3_name,
        "inner_way_3_level": profile.inner_way_3_level,
        "inner_way_4_name": profile.inner_way_4_name,
        "inner_way_4_level": profile.inner_way_4_level,
        "build_link": profile.build_link,
        "notes": profile.notes,
    }


class BaseRegistrationModal(discord.ui.Modal):
    def __init__(self, bot: "WWMGuildBot"):
        super().__init__()
        self.bot = bot

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        embed = build_simple_embed("Registration Error", str(error), color=0xE74C3C)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


class RegistrationContinueView(discord.ui.View):
    def __init__(self, bot: "WWMGuildBot", user_id: int, next_step: int):
        super().__init__(timeout=900)
        self.bot = bot
        self.user_id = user_id
        self.next_step = next_step

    @discord.ui.button(label="Continue Registration", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Not Your Form",
                    "Only the user who started the registration flow can continue it.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )
            return
        if self.next_step == 2:
            await interaction.response.send_modal(RegisterCharacterStep2Modal(self.bot, interaction.user.id))
            return
        await interaction.response.send_modal(RegisterCharacterStep3Modal(self.bot, interaction.user.id))


class RegisterCharacterStep1Modal(BaseRegistrationModal, title="WWM Registration • Step 1/3"):
    character_name = discord.ui.TextInput(label="Character Name", max_length=80)
    mastery = discord.ui.TextInput(label="Mastery", max_length=80)
    role = discord.ui.TextInput(label="Role: tank/healer/dps", max_length=10)
    primary_weapon = discord.ui.TextInput(label="Primary Weapon", max_length=80)
    secondary_weapon = discord.ui.TextInput(label="Secondary Weapon", max_length=80)

    def __init__(self, bot: "WWMGuildBot", existing: dict | None = None):
        super().__init__(bot)
        existing = existing or {}
        self.character_name.default = existing.get("character_name")
        self.mastery.default = existing.get("mastery")
        self.role.default = existing.get("role")
        self.primary_weapon.default = existing.get("primary_weapon")
        self.secondary_weapon.default = existing.get("secondary_weapon")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        role_value = self.role.value.strip().lower()
        if role_value not in ROLE_BUCKETS:
            raise ValidationError("Role must be tank, healer, or dps.")
        self.bot.registration_sessions[interaction.user.id] = {
            "discord_user_id": interaction.user.id,
            "character_name": self.character_name.value.strip(),
            "mastery": self.mastery.value.strip(),
            "role": role_value,
            "primary_weapon": self.primary_weapon.value.strip(),
            "secondary_weapon": self.secondary_weapon.value.strip(),
        }
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Step 1 Saved",
                "Continue to step 2 for path guide, sect boost, and inner ways 1-3.",
                color=0x2ECC71,
            ),
            view=RegistrationContinueView(self.bot, interaction.user.id, 2),
            ephemeral=True,
        )


class RegisterCharacterStep2Modal(BaseRegistrationModal, title="WWM Registration • Step 2/3"):
    path_guide = discord.ui.TextInput(label="Path Guide", max_length=400)
    sect_boost = discord.ui.TextInput(label="Sect Boost (optional)", required=False, max_length=200)
    inner_way_1 = discord.ui.TextInput(label="Inner Way 1 as Name:Level", max_length=120)
    inner_way_2 = discord.ui.TextInput(label="Inner Way 2 as Name:Level", max_length=120)
    inner_way_3 = discord.ui.TextInput(label="Inner Way 3 as Name:Level", max_length=120)

    def __init__(self, bot: "WWMGuildBot", user_id: int):
        super().__init__(bot)
        session = bot.registration_sessions.get(user_id, {})
        self.path_guide.default = session.get("path_guide")
        self.sect_boost.default = session.get("sect_boost")
        for index in range(1, 4):
            name = session.get(f"inner_way_{index}_name")
            level = session.get(f"inner_way_{index}_level")
            if name is not None and level is not None:
                getattr(self, f"inner_way_{index}").default = f"{name}:{level}"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = self.bot.registration_sessions.get(interaction.user.id)
        if session is None:
            raise ValidationError("Registration session expired. Run /register_character again.")
        session["path_guide"] = self.path_guide.value.strip()
        session["sect_boost"] = normalize_optional_text(self.sect_boost.value)
        for index, value in enumerate(
            [self.inner_way_1.value, self.inner_way_2.value, self.inner_way_3.value],
            start=1,
        ):
            name, level = parse_inner_way_pair(value)
            session[f"inner_way_{index}_name"] = name
            session[f"inner_way_{index}_level"] = level
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Step 2 Saved",
                "Continue to step 3 for inner way 4, optional link, and notes.",
                color=0x2ECC71,
            ),
            view=RegistrationContinueView(self.bot, interaction.user.id, 3),
            ephemeral=True,
        )


class RegisterCharacterStep3Modal(BaseRegistrationModal, title="WWM Registration • Step 3/3"):
    inner_way_4 = discord.ui.TextInput(label="Inner Way 4 as Name:Level", max_length=120)
    build_link = discord.ui.TextInput(label="Build Link (optional)", required=False, max_length=400)
    notes = discord.ui.TextInput(
        label="Notes (optional)",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=600,
    )

    def __init__(self, bot: "WWMGuildBot", user_id: int):
        super().__init__(bot)
        session = bot.registration_sessions.get(user_id, {})
        name = session.get("inner_way_4_name")
        level = session.get("inner_way_4_level")
        if name is not None and level is not None:
            self.inner_way_4.default = f"{name}:{level}"
        self.build_link.default = session.get("build_link")
        self.notes.default = session.get("notes")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = self.bot.registration_sessions.get(interaction.user.id)
        if session is None:
            raise ValidationError("Registration session expired. Run /register_character again.")
        name, level = parse_inner_way_pair(self.inner_way_4.value)
        session["inner_way_4_name"] = name
        session["inner_way_4_level"] = level
        session["build_link"] = normalize_optional_text(self.build_link.value)
        session["notes"] = normalize_optional_text(self.notes.value)
        self.bot.db.upsert_user(session)
        self.bot.registration_sessions.pop(interaction.user.id, None)
        profile = self.bot.db.get_user(interaction.user.id)
        assert profile is not None
        await interaction.response.send_message(
            embed=build_profile_embed(profile, interaction.user),
            ephemeral=True,
        )


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

    @app_commands.command(name="register_character", description="Register or update your one WWM character/build.")
    async def register_character(self, interaction: discord.Interaction) -> None:
        existing = self.bot.db.get_user(interaction.user.id)
        payload = profile_to_payload(existing) if existing else None
        await interaction.response.send_modal(RegisterCharacterStep1Modal(self.bot, payload))

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
                f"Event **#{row['event_id']}** {row['title']} — {position} — {row['status']}"
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
