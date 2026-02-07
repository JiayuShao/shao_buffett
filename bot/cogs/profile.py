"""User profile slash commands."""

import discord
from discord.ext import commands
from storage.repositories.user_repo import UserRepository
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.repositories.notes_repo import NotesRepository
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

    # ── /me — Unified overview ──

    @discord.slash_command(name="me", description="View your full profile: watchlist, portfolio, notes, and settings")
    async def me(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer(ephemeral=True)
        user_id = ctx.author.id

        # Fetch all user data in parallel-ish
        user = await self.repo.get_or_create(user_id)
        watchlist_repo = WatchlistRepository(self.bot.db_pool)
        watchlist = await watchlist_repo.get(user_id)
        notes_repo = NotesRepository(self.bot.db_pool)
        recent_notes = await notes_repo.get_recent(user_id, limit=5)
        action_items = await notes_repo.get_active_action_items(user_id)

        # Portfolio (may not exist yet)
        holdings = []
        fin_profile = None
        try:
            from storage.repositories.portfolio_repo import PortfolioRepository, FinancialProfileRepository
            portfolio_repo = PortfolioRepository(self.bot.db_pool)
            profile_repo = FinancialProfileRepository(self.bot.db_pool)
            holdings = await portfolio_repo.get_holdings(user_id)
            fin_profile = await profile_repo.get(user_id)
        except Exception:
            pass

        # Build the embed
        embed = make_embed(
            f"{ctx.author.display_name} — Overview",
            "",
            color=EmbedColor.INFO,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        # Profile settings
        interests = user.get("interests", {})
        sector_list = interests.get("sectors", [])
        metrics = user.get("focused_metrics", [])
        risk = user.get("risk_tolerance", "moderate")
        notif = user.get("notification_preferences", {})

        profile_lines = [
            f"**Risk:** {risk.title()}",
            f"**Notifications:** {notif.get('delivery', 'channel').title()}",
        ]
        if sector_list:
            profile_lines.append(f"**Sectors:** {', '.join(sector_list)}")
        if metrics:
            profile_lines.append(f"**Metrics:** {', '.join(metrics[:5])}")
        embed.add_field(name="Profile", value="\n".join(profile_lines), inline=False)

        # Watchlist
        if watchlist:
            wl_text = ", ".join(watchlist[:20])
            if len(watchlist) > 20:
                wl_text += f" (+{len(watchlist) - 20} more)"
            embed.add_field(name=f"Watchlist ({len(watchlist)})", value=wl_text, inline=False)
        else:
            embed.add_field(name="Watchlist", value="Empty — use `/watchlist add`", inline=False)

        # Portfolio
        if holdings:
            port_lines = []
            for h in holdings[:10]:
                cost = f" @ ${h['cost_basis']:.2f}" if h.get("cost_basis") else ""
                acct = f" ({h['account_type']})" if h.get("account_type") and h["account_type"] != "taxable" else ""
                port_lines.append(f"**{h['symbol']}** — {h['shares']} shares{cost}{acct}")
            if len(holdings) > 10:
                port_lines.append(f"*+{len(holdings) - 10} more*")
            embed.add_field(name=f"Portfolio ({len(holdings)})", value="\n".join(port_lines), inline=False)
        else:
            embed.add_field(name="Portfolio", value="Empty — use `/portfolio add`", inline=False)

        # Financial profile
        if fin_profile:
            fp_parts = []
            if fin_profile.get("investment_horizon"):
                fp_parts.append(f"**Horizon:** {fin_profile['investment_horizon']}")
            if fin_profile.get("tax_bracket"):
                fp_parts.append(f"**Tax:** {fin_profile['tax_bracket']}")
            if fin_profile.get("goals"):
                goals = fin_profile["goals"]
                if isinstance(goals, list):
                    fp_parts.append(f"**Goals:** {', '.join(goals[:3])}")
            if fin_profile.get("monthly_investment"):
                fp_parts.append(f"**Monthly:** ${fin_profile['monthly_investment']:,.0f}")
            if fp_parts:
                embed.add_field(name="Financial Profile", value="\n".join(fp_parts), inline=False)

        # Action items
        if action_items:
            ai_lines = []
            for item in action_items[:5]:
                symbols = f" [{', '.join(item['symbols'])}]" if item.get("symbols") else ""
                ai_lines.append(f"#{item['id']}{symbols} — {item['content'][:80]}")
            embed.add_field(name=f"Action Items ({len(action_items)})", value="\n".join(ai_lines), inline=False)

        # Recent notes
        if recent_notes:
            note_lines = []
            for n in recent_notes[:5]:
                symbols = f" [{', '.join(n['symbols'])}]" if n.get("symbols") else ""
                note_lines.append(f"[{n['note_type']}]{symbols} {n['content'][:60]}")
            embed.add_field(name="Recent Notes", value="\n".join(note_lines), inline=False)

        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ProfileCog(bot))
