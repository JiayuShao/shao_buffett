# Shao Buffett — Project Memory

## Architecture
- Discord bot (py-cord) + AI engine (Anthropic SDK) + financial data APIs + PostgreSQL
- Async throughout (asyncio, aiohttp, asyncpg)
- Multi-model routing: Haiku (routine), Sonnet (standard), Opus (deep analysis)
- Portfolio-aware routing: upgrades to Sonnet for portfolio decisions
- Web dashboard: Quart + Discord OAuth + Plotly.js
- Personal analyst features: cross-conversation notes, portfolio tracking, proactive insights

## Key Patterns
- All data access goes through `data/manager.py` (caching + rate limiting)
- AI tool-use loop in `ai/engine.py` — Claude calls financial tools, engine executes, loop continues
- Parallel tool execution: tools requested in the same round run with `asyncio.gather()`
- Scheduler parallelism: `asyncio.TaskGroup` for quote fetching, `asyncio.gather(return_exceptions=True)` for independent insight checks
- True streaming: final response uses `client.messages.stream()` for real-time text delivery
- Consolidated tool loop: single `_run_tool_loop()` with `stream_final` parameter replaces two separate methods
- `user_id` threaded through tool loop so note/portfolio tools know who's calling
- System prompt injected with user's notes, portfolio, and financial profile before each chat
- Activity logging extracts mentioned symbols and classifies query type
- Notifications: processors detect changes → create Notification objects → dispatcher routes to users
- Proactive insights: scheduler cross-references portfolio with market data every 30 min
  - Price movement alerts (>3% daily moves)
  - Earnings calendar digests (weekly, when 2+ holdings report)
  - Insider trading alerts ($500K+ transactions)
  - Auto-AI earnings transcript analysis (within 48h of reporting)
- Factor grades: quantitative A+-F ratings across 5 dimensions relative to sector peers
- Scheduler uses `discord.ext.tasks` for periodic polling
- Repositories provide CRUD for all database tables

## Financial APIs
- Finnhub: quotes, analyst data, earnings, news, insider trades (WebSocket for real-time)
- FRED: 812K+ macro series via fredapi
- MarketAux: financial news with sentiment
- FMP: fundamentals, ratios, earnings transcripts, sector performance
- SEC EDGAR: 10-K, 10-Q, 8-K filings
- arXiv: quantitative finance research papers
- Polymarket: prediction market data (market-implied probabilities for macro/political/crypto events)

## AI Tools (25 total)
- 16 financial data tools (quote, profile, fundamentals, analyst, earnings, news, macro, sector, transcript, filings, papers, polymarket, trending_stocks, sentiment, technical_indicators, generate_chart)
- 2 quantitative tools (get_factor_grades, get_portfolio_health)
- 3 note tools (save_note, get_user_notes, resolve_action_item)
- 4 portfolio tools (get_portfolio, update_portfolio, get_financial_profile, update_financial_profile)

## Database Tables
- `user_profiles`, `watchlists`, `price_alerts`, `conversations`, `dashboards`, `notification_log`, `data_cache` (migration 001)
- `conversation_notes` — cross-conversation memory with note types and symbol tagging (migration 002)
- `portfolio_holdings`, `financial_profile` — portfolio tracking with account types (migration 003)
- `user_activity`, `proactive_insights` — activity tracking and insight queue (migration 004)

## Running
```bash
# Development
docker compose up db         # Start PostgreSQL only
source .venv/bin/activate    # Activate virtual environment
python -m bot.main           # Run bot

# Production
docker compose up -d         # Start everything

# Tests
source .venv/bin/activate
python -m pytest tests/
```

## File Layout
- `bot/` — Discord bot, cogs (slash commands), event handlers
  - `bot/cogs/notes.py` — /notes show, /notes actions, /notes resolve, /notes delete
  - `bot/cogs/portfolio.py` — /portfolio show, /portfolio add, /portfolio remove, /portfolio goals
  - `bot/cogs/report.py` — /report <symbol> (structured Opus-powered analyst report)
- `ai/` — Claude API integration, model routing, tools, prompts
- `data/` — Financial data collectors, processors, cache, rate limiter
  - `data/collectors/polymarket.py` — Polymarket prediction market API
  - `data/processors/factor_processor.py` — Factor grade computation engine (Value, Growth, Profitability, Momentum, EPS Revisions)
- `notifications/` — Dispatcher, formatter, filters, types
- `scheduler/` — Periodic tasks, morning/evening briefings, proactive insights
  - `scheduler/proactive.py` — ProactiveInsightGenerator
- `dashboard/` — Plotly chart generation and rendering
- `web/` — Quart web dashboard with Discord OAuth
- `storage/` — Database, migrations, repositories
  - `storage/repositories/notes_repo.py` — NotesRepository
  - `storage/repositories/portfolio_repo.py` — PortfolioRepository + FinancialProfileRepository
  - `storage/repositories/activity_repo.py` — ActivityRepository + ProactiveInsightRepository
- `utils/` — Formatting, time, retry, embed builder
- `config/` — Settings, constants, logging
