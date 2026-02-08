---
name: add-discord-cog
description: Add a new slash command group as a py-cord cog. Covers the 2-file workflow (bot/cogs/ → bot/main.py) with all gotchas.
---

# Add a Discord Cog

Cogs are py-cord extensions that group related slash commands. Each cog is a separate file in `bot/cogs/`.

## Step 1: Create the cog file in `bot/cogs/<name>.py`

```python
"""<Description> slash commands."""

import discord
from discord.ext import commands
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor


class ExampleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # --- Slash command group ---
    example = discord.SlashCommandGroup("example", "Example commands")

    @example.command(description="Do something useful")
    async def action(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        limit: discord.Option(int, "Max results", default=5),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()  # ALWAYS defer before async work

        try:
            data = await self.bot.data_manager.get_quote(symbol.upper())
        except Exception:
            await ctx.respond(embed=error_embed("Failed to fetch data."), ephemeral=True)
            return

        embed = make_embed(
            f"Example — {symbol.upper()}",
            f"Price: ${data.get('price', 0):.2f}",
            color=EmbedColor.INFO,
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ExampleCog(bot))
```

### Key patterns
- **Always `await ctx.defer()`** before any async operation. Discord requires a response within 3 seconds — `defer()` buys you 15 minutes.
- **`# type: ignore[valid-type]`** is required on every `discord.Option()` parameter. py-cord's type stubs don't match the runtime behavior.
- **`def setup(bot)` is mandatory** — py-cord calls this to register the cog.
- Access services via `self.bot`:
  - `self.bot.data_manager` — all financial data
  - `self.bot.ai_engine` — Claude API (for `chat()`, `analyze()`)
  - `self.bot.db_pool` — direct DB access (prefer repositories)
  - `self.bot.notification_dispatcher` — send notifications

### Embed helpers (from `utils/embed_builder.py`)
- `make_embed(title, description, color)` — standard embed
- `error_embed(message)` — red error embed
- `success_embed(message)` — green success embed
- `price_embed(symbol, price, change, change_pct)` — stock price embed
- `news_embed(title, source, summary)` — news article embed

### EmbedColor constants (from `config/constants.py`)
`SUCCESS`, `WARNING`, `ERROR`, `INFO`, `BULLISH`, `BEARISH`, `NEUTRAL`, `EARNINGS`, `NEWS`, `ALERT`, `MACRO`, `RESEARCH`

### Standalone commands (no group)
For a single command that doesn't need a group, use `@commands.slash_command` directly:

```python
@commands.slash_command(description="Quick price check")
async def price(
    self,
    ctx: discord.ApplicationContext,
    symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
) -> None:
    await ctx.defer()
    ...
```

### Subcommands
For nested commands like `/portfolio add`, `/portfolio remove`:

```python
portfolio = discord.SlashCommandGroup("portfolio", "Portfolio management")

@portfolio.command(description="Add a holding")
async def add(self, ctx, ...):
    ...

@portfolio.command(description="Remove a holding")
async def remove(self, ctx, ...):
    ...
```

## Step 2: Register in `bot/main.py`

Add the module path to the `cog_modules` list:

```python
cog_modules = [
    "bot.cogs.watchlist",
    "bot.cogs.alerts",
    ...
    "bot.cogs.example",  # <-- add here
]
```

The bot loads cogs sequentially at startup via `bot.load_extension(module)`.

## Gotchas

- **Ephemeral errors**: use `ephemeral=True` on error responses so only the user sees them
- **Option types**: `str`, `int`, `float`, `bool`, `discord.Member`, `discord.TextChannel`
- **Autocomplete**: use `discord.Option(str, autocomplete=my_autocomplete_fn)` for dynamic choices
- **Permissions**: use `@commands.has_permissions(administrator=True)` for admin-only commands
- **Formatting helpers**: import from `utils/formatting.py` — `format_percent()`, `format_change()`, `format_number()`, `truncate()`
- **Long responses**: Discord embeds have a 4096 char description limit and 1024 char field limit (constants in `config/constants.py`)

## Checklist

- [ ] Cog file in `bot/cogs/<name>.py`
- [ ] `setup(bot)` function at module level
- [ ] Module registered in `bot/main.py` `cog_modules` list
- [ ] `await ctx.defer()` before all async operations
- [ ] `# type: ignore[valid-type]` on `discord.Option` params
- [ ] Error responses use `error_embed()` with `ephemeral=True`
- [ ] Uses `make_embed` / `EmbedColor` for consistent styling
