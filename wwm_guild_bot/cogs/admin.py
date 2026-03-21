from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..utils import ValidationError, build_simple_embed


class AdminCog(commands.Cog):
    def __init__(self, bot: "WWMGuildBot"):
        self.bot = bot

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)
        embed = build_simple_embed("Admin Error", str(original), color=0xE74C3C)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def ensure_officer(self, interaction: discord.Interaction) -> None:
        if not self.bot.member_is_officer(interaction.user):
            raise ValidationError("Only officers/admins can use this command.")

    @app_commands.command(name="event_close", description="Close signups for an event.")
    async def event_close(self, interaction: discord.Interaction, event_id: int) -> None:
        self.ensure_officer(interaction)
        self.bot.db.update_event_status(event_id, "closed")
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed("Event Closed", f"Event #{event_id} is now closed.", color=0x2ECC71),
            ephemeral=True,
        )

    @app_commands.command(name="event_lock", description="Lock roster changes for an event.")
    async def event_lock(self, interaction: discord.Interaction, event_id: int) -> None:
        self.ensure_officer(interaction)
        self.bot.db.update_event_status(event_id, "locked")
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed("Event Locked", f"Event #{event_id} is now locked.", color=0x2ECC71),
            ephemeral=True,
        )

    @app_commands.command(name="event_unlock", description="Unlock roster changes for an event.")
    async def event_unlock(self, interaction: discord.Interaction, event_id: int) -> None:
        self.ensure_officer(interaction)
        self.bot.db.update_event_status(event_id, "open")
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed("Event Unlocked", f"Event #{event_id} is now open.", color=0x2ECC71),
            ephemeral=True,
        )

    @app_commands.command(name="roster_move", description="Officer override to move a user into a role or state.")
    @app_commands.describe(role_or_state="tank, healer, dps, bench, tentative, or absence")
    async def roster_move(
        self,
        interaction: discord.Interaction,
        event_id: int,
        user: discord.Member,
        role_or_state: str,
    ) -> None:
        self.ensure_officer(interaction)
        role_or_state = role_or_state.strip().lower()
        event, _profile = await self.bot.ensure_signup_allowed(event_id, user, officer_override=True)
        if role_or_state in {"tank", "healer", "dps"}:
            self.bot.db.upsert_signup(event_id, user.id, "main", role_or_state)
        elif role_or_state == "bench":
            self.bot.db.upsert_signup(event_id, user.id, "bench", None)
        elif role_or_state == "tentative":
            if not event.allow_tentative:
                raise ValidationError("Tentative signups are disabled for this event.")
            self.bot.db.upsert_signup(event_id, user.id, "tentative", None)
        elif role_or_state == "absence":
            self.bot.db.upsert_signup(event_id, user.id, "absence", None)
        else:
            raise ValidationError("role_or_state must be tank, healer, dps, bench, tentative, or absence.")
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Roster Updated",
                f"Moved {user.mention} to **{role_or_state}** for event #{event_id}.",
                color=0x2ECC71,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="roster_remove", description="Officer override to remove a user signup.")
    async def roster_remove(
        self,
        interaction: discord.Interaction,
        event_id: int,
        user: discord.Member,
    ) -> None:
        self.ensure_officer(interaction)
        self.bot.db.delete_signup(event_id, user.id)
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Signup Removed",
                f"Removed {user.mention} from event #{event_id}.",
                color=0x2ECC71,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="event_refresh", description="Re-render the signup message from SQLite.")
    async def event_refresh(self, interaction: discord.Interaction, event_id: int) -> None:
        self.ensure_officer(interaction)
        await self.bot.refresh_event_message(event_id)
        await interaction.response.send_message(
            embed=build_simple_embed("Event Refreshed", f"Event #{event_id} was refreshed.", color=0x2ECC71),
            ephemeral=True,
        )

    @app_commands.command(name="template_toggle", description="Activate or deactivate a recurring template.")
    async def template_toggle(self, interaction: discord.Interaction, template_id: int, active: bool) -> None:
        self.ensure_officer(interaction)
        template = self.bot.db.get_template(template_id)
        if template is None:
            raise ValidationError(f"Template #{template_id} does not exist.")
        self.bot.db.set_template_active(template_id, active)
        status = "active" if active else "inactive"
        await interaction.response.send_message(
            embed=build_simple_embed(
                "Template Updated",
                f"Template #{template_id} is now **{status}**.",
                color=0x2ECC71,
            ),
            ephemeral=True,
        )


async def setup(bot: "WWMGuildBot") -> None:
    cog = AdminCog(bot)
    await bot.add_cog(cog, guild=bot.guild_object)
