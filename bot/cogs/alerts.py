"""Price alert slash commands."""

import discord
from discord.ext import commands
from storage.repositories.alert_repo import AlertRepository
from utils.formatting import validate_ticker, format_currency
from utils.embed_builder import make_embed, error_embed, success_embed
from config.constants import EmbedColor


class AlertsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def repo(self) -> AlertRepository:
        return AlertRepository(self.bot.db_pool)

    alert = discord.SlashCommandGroup("alert", "Manage price alerts")

    @alert.command(description="Set a price alert")
    async def set(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        condition: discord.Option(str, "Alert condition", choices=["above", "below", "change_pct"]),  # type: ignore[valid-type]
        threshold: discord.Option(float, "Price threshold or percentage"),  # type: ignore[valid-type]
    ) -> None:
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        alert_id = await self.repo.create(ctx.author.id, ticker, condition, threshold)
        if alert_id:
            if condition == "change_pct":
                desc = f"Alert #{alert_id}: **{ticker}** changes by {threshold:+.1f}%"
            else:
                desc = f"Alert #{alert_id}: **{ticker}** goes {condition} {format_currency(threshold)}"
            await ctx.respond(embed=success_embed(desc))
        else:
            await ctx.respond(embed=error_embed("Alert limit reached. Remove some alerts first."), ephemeral=True)

    @alert.command(description="Remove a price alert")
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        alert_id: discord.Option(int, "Alert ID to remove"),  # type: ignore[valid-type]
    ) -> None:
        removed = await self.repo.remove(alert_id, ctx.author.id)
        if removed:
            await ctx.respond(embed=success_embed(f"Alert #{alert_id} removed."))
        else:
            await ctx.respond(embed=error_embed("Alert not found or doesn't belong to you."), ephemeral=True)

    @alert.command(name="list", description="List your active alerts")
    async def list_alerts(self, ctx: discord.ApplicationContext) -> None:
        alerts = await self.repo.get_active(ctx.author.id)

        if not alerts:
            await ctx.respond(embed=make_embed(
                "Your Alerts",
                "No active alerts. Use `/alert set` to create one.",
                color=EmbedColor.INFO,
            ))
            return

        lines = []
        for a in alerts:
            cond = a["condition"]
            if cond == "change_pct":
                desc = f"changes by {float(a['threshold']):+.1f}%"
            else:
                desc = f"goes {cond} {format_currency(float(a['threshold']))}"
            lines.append(f"#{a['id']} — **{a['symbol']}** {desc}")

        embed = make_embed(
            f"Your Alerts ({len(alerts)} active)",
            "\n".join(lines),
            color=EmbedColor.ALERT,
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(AlertsCog(bot))
