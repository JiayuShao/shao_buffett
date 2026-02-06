"""Slash commands for portfolio management."""

import discord
from discord.ext import commands
from storage.repositories.portfolio_repo import PortfolioRepository, FinancialProfileRepository
from utils.formatting import validate_ticker, format_currency
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor


class PortfolioCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    portfolio = discord.SlashCommandGroup("portfolio", "Manage your portfolio")

    @portfolio.command(description="Show your portfolio holdings")
    async def show(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer(ephemeral=True)
        repo = PortfolioRepository(self.bot.db_pool)
        holdings = await repo.get_holdings(ctx.author.id)

        if not holdings:
            await ctx.respond(
                embed=make_embed(
                    "Your Portfolio",
                    "No holdings yet. Tell me about your positions in chat or use `/portfolio add`.",
                    color=EmbedColor.INFO,
                ),
                ephemeral=True,
            )
            return

        lines = []
        for h in holdings:
            cost = f" @ {format_currency(float(h['cost_basis']))}" if h.get("cost_basis") else ""
            acct = f" ({h['account_type']})" if h["account_type"] != "taxable" else ""
            notes_str = f" — {h['notes'][:50]}" if h.get("notes") else ""
            lines.append(f"**{h['symbol']}**: {h['shares']} shares{cost}{acct}{notes_str}")

        embed = make_embed(
            f"Your Portfolio ({len(holdings)} positions)",
            "\n".join(lines),
            color=EmbedColor.INFO,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @portfolio.command(description="Add a position to your portfolio")
    async def add(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        shares: discord.Option(float, "Number of shares"),  # type: ignore[valid-type]
        cost_basis: discord.Option(float, "Cost per share", required=False, default=None),  # type: ignore[valid-type]
        account_type: discord.Option(  # type: ignore[valid-type]
            str,
            "Account type",
            choices=["taxable", "ira", "roth_ira", "401k"],
            required=False,
            default="taxable",
        ),
    ) -> None:
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        repo = PortfolioRepository(self.bot.db_pool)
        await repo.upsert(
            discord_id=ctx.author.id,
            symbol=ticker,
            shares=shares,
            cost_basis=cost_basis,
            account_type=account_type,
        )

        cost_str = f" at {format_currency(cost_basis)}/share" if cost_basis else ""
        await ctx.respond(
            embed=make_embed(
                "Position Updated",
                f"**{ticker}**: {shares} shares{cost_str} ({account_type})",
                color=EmbedColor.SUCCESS,
            ),
            ephemeral=True,
        )

    @portfolio.command(description="Remove a position from your portfolio")
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        account_type: discord.Option(  # type: ignore[valid-type]
            str,
            "Account type",
            choices=["taxable", "ira", "roth_ira", "401k"],
            required=False,
            default="taxable",
        ),
    ) -> None:
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        repo = PortfolioRepository(self.bot.db_pool)
        removed = await repo.remove(ctx.author.id, ticker, account_type)

        if removed:
            await ctx.respond(
                embed=make_embed("Position Removed", f"Removed **{ticker}** ({account_type}) from portfolio.", color=EmbedColor.SUCCESS),
                ephemeral=True,
            )
        else:
            await ctx.respond(
                embed=error_embed(f"No {ticker} position found in {account_type} account."),
                ephemeral=True,
            )

    @portfolio.command(description="View or set your financial goals")
    async def goals(
        self,
        ctx: discord.ApplicationContext,
        goal: discord.Option(str, "Add a financial goal (leave empty to view)", required=False, default=None),  # type: ignore[valid-type]
    ) -> None:
        repo = FinancialProfileRepository(self.bot.db_pool)
        profile = await repo.get(ctx.author.id)

        if goal:
            existing_goals = profile.get("goals", []) if profile else []
            if isinstance(existing_goals, list):
                existing_goals.append(goal)
            else:
                existing_goals = [goal]
            await repo.upsert(discord_id=ctx.author.id, goals=existing_goals)
            await ctx.respond(
                embed=make_embed("Goal Added", f"Added: {goal}", color=EmbedColor.SUCCESS),
                ephemeral=True,
            )
        else:
            goals_list = profile.get("goals", []) if profile else []
            if not goals_list:
                await ctx.respond(
                    embed=make_embed("Financial Goals", "No goals set. Add one with `/portfolio goals goal:...`", color=EmbedColor.INFO),
                    ephemeral=True,
                )
                return
            lines = [f"• {g}" for g in goals_list]
            await ctx.respond(
                embed=make_embed("Your Financial Goals", "\n".join(lines), color=EmbedColor.INFO),
                ephemeral=True,
            )


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PortfolioCog(bot))
