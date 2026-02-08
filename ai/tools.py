"""Claude tool definitions for financial data access and personal analyst features."""

# Tool definitions following the Anthropic tool-use format
FINANCIAL_TOOLS = [
    {
        "name": "get_quote",
        "description": (
            "Get the current stock price quote for a ticker symbol. Returns price, change, "
            "change%, high, low, open, previous close. Use this for quick price checks or when "
            "the user asks 'what's X at?' NOT for detailed financial analysis — use get_fundamentals for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, MSFT, GOOGL)",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_company_profile",
        "description": (
            "Get company overview: sector, industry, market cap, description, CEO, employees, IPO date. "
            "Use this when the user asks 'what does X do?', for sector classification, or to understand "
            "a company's business. NOT for financial metrics — use get_fundamentals for valuation/profitability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_fundamentals",
        "description": (
            "Get detailed financial metrics and valuation ratios: PE, EPS, revenue growth, profit margins, "
            "ROE, debt-to-equity, free cash flow, price-to-book, etc. Use for valuation questions, "
            "'is X overvalued?', comparing financial health, or any investment analysis. "
            "For a complete picture, combine with get_analyst_data (Wall Street consensus) and "
            "get_factor_grades (quantitative ratings)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_analyst_data",
        "description": (
            "Get Wall Street analyst consensus: buy/hold/sell recommendations, consensus price target, "
            "and recent upgrades/downgrades. Use when the user asks about analyst opinions, price targets, "
            "or 'what do analysts think about X?' Combine with get_factor_grades to compare quantitative "
            "vs. qualitative ratings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_earnings",
        "description": (
            "Get historical earnings data: EPS actual vs estimate, revenue, and earnings surprises for "
            "recent quarters. Use when discussing earnings performance, beat/miss history, or earnings trends. "
            "For earnings call details, use get_earnings_transcript instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "Get latest financial news articles with sentiment scores. Optionally filter by stock symbol. "
            "Use for 'what's happening with X?', market news updates, or when recent events could affect "
            "a stock. For macro/economic news, prefer get_macro_data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol to filter news (optional, omit for general market news)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return (default 5)",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_macro_data",
        "description": (
            "Get macroeconomic data from FRED. Provide a series_id for a specific indicator (GDP, CPIAUCSL, "
            "UNRATE, FEDFUNDS, DGS10, VIXCLS, DGS2) or omit for a snapshot of all key indicators. "
            "Use for macro environment questions, interest rates, inflation, unemployment, or 'is this "
            "risk-on or risk-off?' NOT for stock-specific data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "string",
                    "description": "FRED series ID (e.g. GDP, CPIAUCSL, UNRATE, FEDFUNDS, DGS10, VIXCLS). Omit for a snapshot of all key macro indicators.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_sector_performance",
        "description": (
            "Get performance data for all market sectors (Technology, Healthcare, Finance, etc.). "
            "Use for sector rotation analysis, 'which sectors are leading?', or to provide context "
            "on how a stock's sector is performing relative to the market."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_earnings_transcript",
        "description": (
            "Get the full earnings call transcript for a specific quarter. Use when the user asks about "
            "management commentary, guidance details, or 'what did the CEO say about X?' Requires symbol, "
            "year, and quarter. For just earnings numbers (EPS, revenue), use get_earnings instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "year": {
                    "type": "integer",
                    "description": "Fiscal year (e.g. 2024)",
                },
                "quarter": {
                    "type": "integer",
                    "description": "Fiscal quarter (1-4)",
                },
            },
            "required": ["symbol", "year", "quarter"],
        },
    },
    {
        "name": "get_sec_filings",
        "description": (
            "Get SEC filings (10-K, 10-Q, 8-K) for a company from EDGAR. Use for regulatory filings, "
            "risk factor changes, material events, or when the user asks about official company disclosures. "
            "For financial data, prefer get_fundamentals (faster and structured)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "form_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of filings to retrieve (e.g. ['10-K', '10-Q', '8-K']). Defaults to all.",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_research_papers",
        "description": (
            "Search for quantitative finance research papers from arXiv. Topics include portfolio "
            "optimization, risk management, ML in finance, factor investing, etc. Use when the user "
            "asks about academic research, methodology, or wants evidence-based strategies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'portfolio optimization deep learning'). Omit for recent papers.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum papers to return (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_polymarket",
        "description": (
            "Get prediction market data from Polymarket — market-implied probabilities for macro, political, "
            "crypto, or other events. Use when discussing Fed rate decisions, elections, regulatory outcomes, "
            "recession odds, or any event where 'what does the market think?' is relevant. "
            "NOT for stock-specific data — use get_quote/get_fundamentals for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for prediction markets (e.g. 'Fed rate cut', 'Bitcoin 100k', 'recession 2025')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of markets to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_trending_stocks",
        "description": (
            "Get stocks currently trending in financial news, ranked by news volume with sentiment breakdown. "
            "Shows which tickers have the most media attention right now and whether coverage is positive or negative. "
            "Use when the user asks 'what's trending?', 'what's in the news?', 'what stocks are hot?', or "
            "for market pulse checks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of trending stocks to return (default 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_sentiment",
        "description": (
            "Get news sentiment time series for one or more stocks — shows how media sentiment has trended "
            "over recent days. Returns daily article counts and average sentiment (-1 to +1) per symbol. "
            "Use when the user asks about sentiment, media tone, 'what does the market think about X?', "
            "or to compare sentiment across multiple tickers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock ticker symbols (e.g. ['AAPL', 'TSLA'])",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of sentiment history (default 7)",
                    "default": 7,
                },
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_technical_indicators",
        "description": (
            "Get technical analysis indicators: SMA (20/50/200-day), RSI (14), EMA (12/26), MACD. "
            "Use for trend direction, support/resistance levels, overbought/oversold signals, or momentum analysis. "
            "Combine with get_fundamentals for a complete fundamental + technical picture."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "generate_chart",
        "description": (
            "Generate a visual chart and send it to Discord. Use when the user asks to 'show me', "
            "'chart', 'graph', or 'visualize' something. Available types: comparison (multi-stock), "
            "sector_heatmap, earnings_history, macro_trend, price_chart."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["comparison", "sector_heatmap", "earnings_history", "macro_trend", "price_chart"],
                    "description": "Type of chart to generate",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Stock symbols for the chart (for comparison/price charts)",
                },
                "series_id": {
                    "type": "string",
                    "description": "FRED series ID (for macro_trend charts)",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
            },
            "required": ["chart_type"],
        },
    },
    # --- Factor Grades & Quant Rating ---
    {
        "name": "get_factor_grades",
        "description": (
            "Get quantitative factor grades (A+ to F) for a stock across 5 dimensions: Value, Growth, "
            "Profitability, Momentum, and EPS Revisions — all computed relative to sector peers. Also returns "
            "a composite Quant Rating (1.0-5.0, Strong Sell to Strong Buy). Use this for investment quality "
            "assessment, 'is X a good stock?', or to compare ratings vs Wall Street consensus from get_analyst_data. "
            "This is the quantitative rating — combine with get_analyst_data for a complete picture."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_portfolio_health",
        "description": (
            "Get a comprehensive health check of the user's portfolio: aggregate quality score (weighted "
            "factor grades), sector concentration analysis, weakest holdings, diversification assessment, "
            "and specific improvement suggestions. Use when the user asks about portfolio risk, allocation, "
            "'how is my portfolio?', or for periodic portfolio reviews."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # --- Personal Analyst Tools ---
    {
        "name": "save_note",
        "description": (
            "Save a note about the user for cross-conversation memory. Use this PROACTIVELY when the user "
            "shares financial info, makes decisions, expresses concerns, or when key insights emerge. "
            "Do NOT ask permission — just save it. This is how you remember things across conversations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note_type": {
                    "type": "string",
                    "enum": ["insight", "decision", "action_item", "preference", "concern"],
                    "description": "Type of note: insight (analytical finding), decision (user's choice), action_item (something to follow up on), preference (user preference), concern (worry or risk)",
                },
                "content": {
                    "type": "string",
                    "description": "The note content — be specific and include relevant numbers/dates",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Related stock ticker symbols (optional)",
                },
            },
            "required": ["note_type", "content"],
        },
    },
    {
        "name": "get_user_notes",
        "description": (
            "Retrieve the user's saved notes for context. Use at the start of substantive conversations "
            "to recall what you know about this user, or when discussing a topic the user has previously "
            "mentioned. Filter by type, symbols, or search content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note_type": {
                    "type": "string",
                    "enum": ["insight", "decision", "action_item", "preference", "concern"],
                    "description": "Filter by note type (optional, omit for all types)",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by related symbols (optional)",
                },
                "query": {
                    "type": "string",
                    "description": "Search note content (optional)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "resolve_action_item",
        "description": "Mark an action item as resolved/complete. Use when the user says they've done something from their action items list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "The ID of the action item to resolve",
                }
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "get_portfolio",
        "description": (
            "Get the user's portfolio holdings: symbols, shares, cost basis, and account type. "
            "Use when discussing portfolio value, allocation, specific positions, or before giving "
            "investment advice. For a health assessment, use get_portfolio_health instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_portfolio",
        "description": (
            "Add, update, or remove a position in the user's portfolio. Use when the user mentions "
            "buying, selling, or adjusting positions (e.g. 'I bought 100 AAPL at $185'). Always confirm "
            "the details before removing positions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove"],
                    "description": "Whether to add/update or remove the position",
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "shares": {
                    "type": "number",
                    "description": "Number of shares (for add/update)",
                },
                "cost_basis": {
                    "type": "number",
                    "description": "Cost per share (optional)",
                },
                "account_type": {
                    "type": "string",
                    "enum": ["taxable", "ira", "roth_ira", "401k"],
                    "description": "Account type (default: taxable)",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the position",
                },
            },
            "required": ["action", "symbol"],
        },
    },
    {
        "name": "get_financial_profile",
        "description": (
            "Get the user's financial profile: income, goals, investment horizon, and tax bracket. "
            "Use before giving personalized advice to understand the user's financial situation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_financial_profile",
        "description": (
            "Update the user's financial profile when they share financial details in conversation "
            "(income, goals, horizon, tax info). Use PROACTIVELY — don't ask permission, just save it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "annual_income": {
                    "type": "number",
                    "description": "Annual income in USD",
                },
                "investment_horizon": {
                    "type": "string",
                    "description": "Investment time horizon (e.g. '5-10 years', 'long-term', 'retirement in 20 years')",
                },
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Financial goals (replaces existing goals)",
                },
                "tax_bracket": {
                    "type": "string",
                    "description": "Tax bracket (e.g. '24%', '32%')",
                },
                "monthly_investment": {
                    "type": "number",
                    "description": "Monthly investment amount in USD",
                },
            },
            "required": [],
        },
    },
]
