"""User profile slash commands."""

import discord
from discord.ext import commands
from storage.repositories.user_repo import UserRepository
from utils.embed_builder import make_embed, success_embed
from config.constants import EmbedColor, SECTORS, METRIC_OPTIONS, RiskTolerance


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def repo(self) -> UserRepository:
        return UserRepository(self.bot.db_pool)

    profile = discord.SlashCommandGroup("profile", "Manage your user profile")

    @profile.command(description="View your profile settings")
    async def show(self, ctx: discord.ApplicationContext) -> None:
        user = await self.repo.get_or_create(ctx.author.id)

        interests = user.get("interests", {})
        sectors = interests.get("sectors", [])
        metrics = user.get("focused_metrics", [])
        risk = user.get("risk_tolerance", "moderate")
        notif = user.get("notification_preferences", {})

        embed = make_embed(
            f"Profile — {ctx.author.display_name}",
            "",
            color=EmbedColor.INFO,
        )
        embed.add_field(name="Sectors", value=", ".join(sectors) if sectors else "Not set", inline=False)
        embed.add_field(name="Focused Metrics", value=", ".join(metrics) if metrics else "Not set", inline=False)
        embed.add_field(name="Risk Tolerance", value=risk.title(), inline=True)
        embed.add_field(name="Delivery", value=notif.get("delivery", "channel").title(), inline=True)

        await ctx.respond(embed=embed, ephemeral=True)

    @profile.command(description="Set your interested sectors")
    async def sectors(
        self,
        ctx: discord.ApplicationContext,
        sectors: discord.Option(str, "Comma-separated sectors (e.g. Technology, Healthcare)"),  # type: ignore[valid-type]
    ) -> None:
        sector_list = [s.strip() for s in sectors.split(",") if s.strip()]
        interests = {"sectors": sector_list}
        await self.repo.update_interests(ctx.author.id, interests)
        await ctx.respond(embed=success_embed(f"Sectors updated: {', '.join(sector_list)}"), ephemeral=True)

    @profile.command(description="Set your focused metrics")
    async def metrics(
        self,
        ctx: discord.ApplicationContext,
        metrics: discord.Option(str, "Comma-separated metrics (e.g. pe_ratio, eps, revenue_growth)"),  # type: ignore[valid-type]
    ) -> None:
        metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
        valid = [m for m in metric_list if m in METRIC_OPTIONS]
        if not valid:
            options = ", ".join(METRIC_OPTIONS)
            await ctx.respond(
                embed=make_embed("Invalid Metrics", f"Valid options: {options}", color=EmbedColor.WARNING),
                ephemeral=True,
            )
            return
        await self.repo.update_metrics(ctx.author.id, valid)
        await ctx.respond(embed=success_embed(f"Metrics updated: {', '.join(valid)}"), ephemeral=True)

    @profile.command(description="Set your risk tolerance")
    async def risk(
        self,
        ctx: discord.ApplicationContext,
        level: discord.Option(str, "Risk tolerance", choices=["conservative", "moderate", "aggressive"]),  # type: ignore[valid-type]
    ) -> None:
        await self.repo.update_risk_tolerance(ctx.author.id, level)
        await ctx.respond(embed=success_embed(f"Risk tolerance set to **{level}**."), ephemeral=True)

    @profile.command(description="Set notification preferences")
    async def notifications(
        self,
        ctx: discord.ApplicationContext,
        delivery: discord.Option(str, "How to receive notifications", choices=["channel", "dm"]),  # type: ignore[valid-type]
    ) -> None:
        prefs = {"delivery": delivery, "quiet_hours": None}
        await self.repo.update_notifications(ctx.author.id, prefs)
        await ctx.respond(embed=success_embed(f"Notifications will be sent via **{delivery}**."), ephemeral=True)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ProfileCog(bot))
