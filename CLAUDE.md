# Buffet Shao — Project Memory

## Architecture
- Discord bot (py-cord) + AI engine (Anthropic SDK) + financial data APIs + PostgreSQL
- Async throughout (asyncio, aiohttp, asyncpg)
- Multi-model routing: Haiku (routine), Sonnet (standard), Opus (deep analysis)
- Web dashboard: Quart + Discord OAuth + Plotly.js

## Key Patterns
- All data access goes through `data/manager.py` (caching + rate limiting)
- AI tool-use loop in `ai/engine.py` — Claude calls financial tools, engine executes, loop continues
- Notifications: processors detect changes → create Notification objects → dispatcher routes to users
- Scheduler uses `discord.ext.tasks` for periodic polling
- Repositories provide CRUD for all database tables

## Financial APIs
- Finnhub: quotes, analyst data, earnings, news, insider trades (WebSocket for real-time)
- FRED: 812K+ macro series via fredapi
- MarketAux: financial news with sentiment
- FMP: fundamentals, ratios, earnings transcripts, sector performance
- SEC EDGAR: 10-K, 10-Q, 8-K filings
- arXiv: quantitative finance research papers

## Running
```bash
# Development
docker compose up db         # Start PostgreSQL only
python -m bot.main           # Run bot

# Production
docker compose up -d         # Start everything
```

## File Layout
- `bot/` — Discord bot, cogs (slash commands), event handlers
- `ai/` — Claude API integration, model routing, tools, prompts
- `data/` — Financial data collectors, processors, cache, rate limiter
- `notifications/` — Dispatcher, formatter, filters, types
- `scheduler/` — Periodic tasks, morning/evening briefings
- `dashboard/` — Plotly chart generation and rendering
- `web/` — Quart web dashboard with Discord OAuth
- `storage/` — Database, migrations, repositories
- `utils/` — Formatting, time, retry, embed builder
- `config/` — Settings, constants, logging
