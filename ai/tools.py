"""Claude tool definitions for financial data access and personal analyst features."""

# Tool definitions following the Anthropic tool-use format
FINANCIAL_TOOLS = [
    {
        "name": "get_quote",
        "description": "Get the current stock price quote for a ticker symbol. Returns price, change, change%, high, low, open, previous close.",
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
        "description": "Get company profile information including sector, industry, market cap, description, CEO, employees, IPO date.",
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
        "description": "Get key financial metrics and ratios: PE ratio, EPS, revenue growth, profit margins, ROE, debt-to-equity, free cash flow, etc.",
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
        "description": "Get analyst recommendations (buy/hold/sell), consensus price target, and recent upgrades/downgrades for a stock.",
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
        "description": "Get historical earnings data including EPS actual vs estimate, revenue, and earnings surprises.",
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
        "description": "Get latest financial news articles, optionally filtered by stock symbol. Includes sentiment scores.",
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
        "description": "Get macroeconomic data from FRED. Can get specific series (e.g. GDP, CPI, UNRATE, FEDFUNDS, DGS10) or a snapshot of all key indicators.",
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
        "description": "Get performance data for all market sectors (Technology, Healthcare, Finance, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_earnings_transcript",
        "description": "Get the earnings call transcript for a company for a specific quarter.",
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
        "description": "Get SEC filings (10-K, 10-Q, 8-K) for a company from EDGAR.",
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
        "description": "Search for quantitative finance research papers from arXiv. Topics include portfolio optimization, risk management, ML in finance, etc.",
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
        "description": "Get prediction market data from Polymarket for macro, political, crypto, or other event outcomes. Returns market-implied probabilities. Useful for gauging market sentiment on Fed rate decisions, elections, regulatory actions, crypto milestones, and geopolitical events.",
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
    # --- Personal Analyst Tools ---
    {
        "name": "save_note",
        "description": "Save a note about the user for cross-conversation memory. Use this proactively when the user shares financial info, makes decisions, expresses concerns, or when key insights emerge. Do NOT ask permission — just save it.",
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
        "description": "Retrieve the user's saved notes for context. Use at the start of substantive conversations or when discussing topics the user has previously mentioned.",
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
        "description": "Mark an action item as resolved/complete.",
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
        "description": "Get the user's portfolio holdings including symbols, shares, cost basis, and account type. Use this when discussing portfolio value, allocation, or specific positions.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_portfolio",
        "description": "Add, update, or remove a position in the user's portfolio. Use when the user mentions buying, selling, or adjusting positions (e.g. 'I bought 100 AAPL at $185').",
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
        "description": "Get the user's financial profile including income, goals, investment horizon, and tax bracket.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_financial_profile",
        "description": "Update the user's financial profile when they share financial details in conversation (income, goals, horizon, tax info).",
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
    {
        "name": "get_technical_indicators",
        "description": "Get technical analysis indicators for a stock: SMA (20/50/200-day), RSI (14), EMA (12/26), MACD. Use for questions about trend direction, support/resistance, overbought/oversold, momentum.",
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
        "description": "Generate a financial chart. Returns a chart image that will be sent to Discord.",
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
                    "description": "Stock symbols for the chart (for comparison charts)",
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
]
