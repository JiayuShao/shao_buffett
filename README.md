# Shao Buffett

AI-powered personal financial analyst Discord bot. Always-on market intelligence with 24 AI tools, cross-conversation memory, portfolio tracking, and proactive insights.

## Features

- **24 AI tools** — Real-time quotes, fundamentals, analyst data, earnings, news, macro, SEC filings, technicals, factor grades, portfolio health, and more
- **6 financial APIs** — Finnhub, FRED, MarketAux, FMP, SEC EDGAR, arXiv
- **Cross-conversation memory** — Saves notes, preferences, and action items across sessions
- **Portfolio tracking** — Holdings with cost basis, financial profile, and goal-aware analysis
- **Proactive insights** — Automatically pushes price move alerts, earnings analysis, insider trade flags, breaking AI news
- **3-tier model routing** — Haiku (routine), Sonnet (standard), Opus (deep research) with portfolio-aware upgrades
- **Dynamic tool filtering** — Haiku gets 12 tools, Sonnet/Opus get all 24
- **Extended thinking** — Sonnet (10K tokens) and Opus (16K tokens) for multi-step reasoning
- **True streaming** — Real-time token streaming with tool call progress indicators
- **Parallel execution** — Independent tool calls, DB queries, and API calls run concurrently
- **Agentic planning** — Tool planning protocol and error recovery for smarter multi-step analysis
- **Context-aware notes** — Symbol-relevant notes prioritized in conversation context
- **Factor grades** — Sector-relative percentile ranking (A+ to F) across Value, Growth, Profitability, Momentum, EPS Revisions

## Architecture

```
bot/          Discord bot (py-cord), slash command cogs, event handlers
ai/           Claude API integration, model routing, 24 tools, system prompts
data/         Financial data collectors, processors, cache, rate limiter
scheduler/    Periodic polling, morning/evening briefings, proactive insights
notifications/  Dispatcher, formatter, filters
storage/      PostgreSQL (asyncpg), migrations, repositories
dashboard/    Plotly chart generation
web/          Quart web dashboard with Discord OAuth
config/       Settings, constants, logging
```

## Requirements

- Python 3.14+
- PostgreSQL 15+
- Discord bot token
- API keys: Anthropic, Finnhub, FRED, MarketAux, FMP

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
python3 -m storage.migrate

# Start
python3 -m bot.main
```

## Docker

```bash
# Development (DB only)
docker compose up db

# Production (uses pinned requirements.lock.txt)
docker compose up -d
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/ask` | Ask anything about markets (streaming) |
| `/research` | Structured research (quick/deep/compare/transcript/filings/papers) |
| `/report` | Opus-powered deep research report |
| `/watchlist` | Manage stock watchlist |
| `/alert` | Price alerts |
| `/portfolio` | Track holdings, cost basis, goals |
| `/notes` | Conversation notes and action items |
| `/market` | Market overview, sectors, macro |
| `/briefing` | Morning/evening briefings |
| `/dashboard` | Visual charts and dashboards |
| `/profile` | User preferences and unified overview |
| `/news` | Financial news feed |
| `/admin` | System health and cache stats |

## Scheduled Tasks

| Task | Interval | Description |
|------|----------|-------------|
| News | 3 min | Poll watchlist news (MarketAux + Finnhub fallback) |
| Price alerts | 60 sec | Check price alert triggers |
| Analyst | 2 hours | Detect rating changes |
| Macro | 1 hour | Monitor economic indicators |
| Proactive insights | 15 min | Price moves, earnings, insider trades, AI news |
| Morning briefing | 9:30 AM ET | Pre-market summary |
| Evening summary | 4:15 PM ET | Post-market recap |

## License

Private.
