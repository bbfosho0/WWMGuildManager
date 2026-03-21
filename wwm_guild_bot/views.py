from __future__ import annotations

import discord

from .utils import build_simple_embed


class SignupView(discord.ui.View):
    def __init__(self, bot: "WWMGuildBot", event_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.event_id = event_id
        self.add_item(
            SignupButton(bot, event_id, "Tank", discord.ButtonStyle.primary, "tank")
        )
        self.add_item(
            SignupButton(bot, event_id, "Healer", discord.ButtonStyle.primary, "healer")
        )
        self.add_item(SignupButton(bot, event_id, "DPS", discord.ButtonStyle.primary, "dps"))
        self.add_item(SignupButton(bot, event_id, "Bench", discord.ButtonStyle.secondary, "bench"))
        self.add_item(
            SignupButton(bot, event_id, "Tentative", discord.ButtonStyle.secondary, "tentative")
        )
        self.add_item(
            SignupButton(bot, event_id, "Absence", discord.ButtonStyle.secondary, "absence")
        )
        self.add_item(
            SignupButton(bot, event_id, "Withdraw", discord.ButtonStyle.danger, "withdraw")
        )
        self.add_item(
            SignupButton(bot, event_id, "Refresh", discord.ButtonStyle.success, "refresh")
        )


class SignupButton(discord.ui.Button[SignupView]):
    def __init__(
        self,
        bot: "WWMGuildBot",
        event_id: int,
        label: str,
        style: discord.ButtonStyle,
        action: str,
    ):
        super().__init__(
            label=label,
            style=style,
            custom_id=f"wwm:event:{event_id}:{action}",
            row=0 if action in {"tank", "healer", "dps", "bench"} else 1,
        )
        self.bot = bot
        self.event_id = event_id
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id == self.bot.user.id:
            return
        try:
            if self.action == "refresh":
                if not self.bot.member_is_officer(interaction.user):
                    await interaction.response.send_message(
                        embed=build_simple_embed(
                            "Officer Only",
                            "Only officer/admin roles can use the refresh button.",
                            color=0xE74C3C,
                        ),
                        ephemeral=True,
                    )
                    return
                await self.bot.refresh_event_message(self.event_id)
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Event Refreshed",
                        f"Event #{self.event_id} was refreshed from SQLite.",
                        color=0x2ECC71,
                    ),
                    ephemeral=True,
                )
                return

            if self.action == "withdraw":
                message = await self.bot.withdraw_signup(self.event_id, interaction.user.id)
            else:
                message = await self.bot.handle_signup_action(
                    event_id=self.event_id,
                    user=interaction.user,
                    action=self.action,
                )
            await interaction.response.send_message(
                embed=build_simple_embed("Signup Updated", message, color=0x2ECC71),
                ephemeral=True,
            )
        except Exception as exc:  # pragma: no cover - Discord interaction error path
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=build_simple_embed(
                        "Action Failed",
                        str(exc),
                        color=0xE74C3C,
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Action Failed",
                        str(exc),
                        color=0xE74C3C,
                    ),
                    ephemeral=True,
                )
