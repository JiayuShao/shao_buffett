"""Admin slash commands — health check, status."""

import discord
from discord.ext import commands
from utils.embed_builder import make_embed
from config.constants import EmbedColor
from ai.router import get_opus_usage


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    admin = discord.SlashCommandGroup("admin", "Bot administration")

    @admin.command(description="Check bot and API health status")
    async def status(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        embed = make_embed(
            "Shao Buffett — System Status",
            "",
            color=EmbedColor.INFO,
        )

        # Bot info
        embed.add_field(
            name="Bot",
            value=f"Guilds: {len(self.bot.guilds)}\nLatency: {self.bot.latency * 1000:.0f}ms",
            inline=True,
        )

        # Opus budget
        used, limit = get_opus_usage()
        embed.add_field(
            name="Opus Budget",
            value=f"{used}/{limit} calls today",
            inline=True,
        )

        # Database
        db_status = "🟢 Connected" if self.bot.db_pool else "🔴 Disconnected"
        embed.add_field(name="Database", value=db_status, inline=True)

        # API health checks
        if self.bot.data_manager:
            try:
                health = await self.bot.data_manager.health_check()
                api_lines = []
                for api, ok in health.items():
                    status = "🟢" if ok else "🔴"
                    api_lines.append(f"{status} {api}")
                embed.add_field(name="APIs", value="\n".join(api_lines), inline=False)
            except Exception:
                embed.add_field(name="APIs", value="⚠️ Health check failed", inline=False)

            # Rate limit usage
            try:
                usage = self.bot.data_manager.rate_limiter.get_usage()
                if usage:
                    usage_lines = []
                    for api, info in sorted(usage.items()):
                        pct = (info["used"] / info["limit"] * 100) if info["limit"] > 0 else 0
                        bar = "🟢" if pct < 80 else ("🟡" if pct < 100 else "🔴")
                        usage_lines.append(f"{bar} {api}: {info['used']}/{info['limit']}")
                    embed.add_field(name="Rate Limits (req/min)", value="\n".join(usage_lines), inline=False)
            except Exception:
                pass

        await ctx.respond(embed=embed)

    @admin.command(description="Get cache statistics")
    async def cache(self, ctx: discord.ApplicationContext) -> None:
        if self.bot.data_manager:
            cache = self.bot.data_manager.cache
            expired = cache.cleanup()
            size = len(cache._store)
            await ctx.respond(
                embed=make_embed(
                    "Cache Stats",
                    f"Entries: {size}\nExpired (cleaned): {expired}",
                    color=EmbedColor.INFO,
                ),
                ephemeral=True,
            )
        else:
            await ctx.respond("Data manager not initialized.", ephemeral=True)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(AdminCog(bot))
