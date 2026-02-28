# Shao Buffett — Project Memory

## Architecture
- Discord bot (py-cord) + AI engine (Anthropic SDK) + financial data APIs + PostgreSQL
- Async throughout (asyncio, aiohttp, asyncpg)
- Multi-model routing: Haiku (routine), Sonnet (standard), Opus (deep analysis)
- Portfolio-aware routing: upgrades to Sonnet for portfolio decisions
- Dynamic tool filtering: Haiku gets 12 tools, Sonnet/Opus get all 24
- Web dashboard: Quart + Discord OAuth + Plotly.js
- Personal analyst features: cross-conversation notes, portfolio tracking, proactive insights

## Key Patterns
- All data access goes through `data/manager.py` (caching + rate limiting)
- AI tool-use loop in `ai/engine.py` — Claude calls financial tools, engine executes, loop continues
- Parallel tool execution: tools requested in the same round run with `asyncio.gather()`
- Parallel DB queries: `_prepare_chat()` and `_inject_user_context()` run independent queries concurrently
- Parallel API calls: `get_fundamentals()` fetches metrics + ratios concurrently
- Scheduler parallelism: `asyncio.TaskGroup` for quote fetching, `asyncio.gather(return_exceptions=True)` for independent insight checks
- True streaming: final response uses `client.messages.stream()` for real-time text delivery
- Consolidated tool loop: single `_run_tool_loop()` with `stream_final` parameter replaces two separate methods
- Tool result capping: `MAX_TOOL_RESULT_CHARS = 12_000` truncates large results with visible marker
- Background summarization: `summarize_if_needed()` runs as fire-and-forget `asyncio.create_task()`
- `user_id` threaded through tool loop so note/portfolio tools know who's calling
- System prompt injected with user's notes (symbol-relevant first), portfolio, and financial profile before each chat
- System prompt includes Tool Planning Protocol and Tool Error Recovery sections
- Conversation history: 15 messages (up from 10), summarization threshold at 20
- Activity logging extracts mentioned symbols and classifies query type
- Notifications: processors detect changes → create Notification objects → dispatcher routes to users
- Proactive insights: scheduler cross-references portfolio with market data every 30 min
  - Price movement alerts (>3% daily moves)
  - Earnings calendar digests (weekly, when 2+ holdings report)
  - Insider trading alerts ($500K+ transactions)
  - Auto-AI earnings transcript analysis (within 48h of reporting)
  - Breaking AI/tech news delivery (all users, capped at 3 per cycle)
- Factor grades: quantitative A+-F ratings across 5 dimensions relative to sector peers
- Pre-compiled regex: router patterns compiled at module load for faster matching
- Opus budget: `_OpusBudget` class (replaces mutable globals) tracks daily usage
- Scheduler uses `discord.ext.tasks` for periodic polling
- Repositories provide CRUD for all database tables

## Financial APIs
- Finnhub: quotes, analyst data, earnings, news, insider trades (WebSocket for real-time)
- FRED: 812K+ macro series via direct HTTP API
- MarketAux: financial news with sentiment
- FMP: fundamentals, ratios, earnings transcripts, sector performance
- SEC EDGAR: 10-K, 10-Q, 8-K filings
- arXiv: quantitative finance research papers + AI/ML research papers

## AI Tools (24 total)
- 15 financial data tools (quote, profile, fundamentals, analyst, earnings, news, macro, sector, transcript, filings, papers, trending_stocks, sentiment, technical_indicators, generate_chart)
- 2 quantitative tools (get_factor_grades, get_portfolio_health)
- 3 note tools (save_note, get_user_notes, resolve_action_item)
- 4 portfolio tools (get_portfolio, update_portfolio, get_financial_profile, update_financial_profile)

## Database Tables
- `user_profiles`, `watchlists`, `price_alerts`, `conversations`, `dashboards`, `notification_log`, `data_cache` (migration 001)
- `conversation_notes` — cross-conversation memory with note types and symbol tagging (migration 002)
- `portfolio_holdings`, `financial_profile` — portfolio tracking with account types (migration 003)
- `user_activity`, `proactive_insights` — activity tracking and insight queue (migration 004)
- Migration 008: adds `ai_news` to proactive_insights CHECK constraint

## Running
```bash
# Development
docker compose up db         # Start PostgreSQL only
source .venv/bin/activate    # Activate virtual environment
python3 -m bot.main          # Run bot

# Production (uses pinned requirements.lock.txt)
docker compose up -d         # Start everything

# Tests
source .venv/bin/activate
python3 -m pytest tests/
```

## File Layout
- `bot/` — Discord bot, cogs (slash commands), event handlers
  - `bot/cogs/notes.py` — /notes show, /notes actions, /notes resolve, /notes delete
  - `bot/cogs/portfolio.py` — /portfolio show, /portfolio add, /portfolio remove, /portfolio goals
  - `bot/cogs/report.py` — /report <symbol> (structured Opus-powered analyst report)
- `ai/` — Claude API integration, model routing, tools, prompts
- `data/` — Financial data collectors, processors, cache, rate limiter
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
- `.claude/skills/` — Claude Code skills for common dev workflows:
  - `add-financial-tool` — Add a new AI tool (tools.py → engine.py → manager.py)
  - `add-discord-cog` — Add a new slash command cog (bot/cogs/ → main.py)
  - `add-db-migration` — Create a database migration (storage/migrations/)
  - `add-data-collector` — Integrate a new financial API (data/collectors/ → manager.py)
