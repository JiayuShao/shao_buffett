"""Claude tool definitions for financial data access."""

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
        "name": "generate_chart",
        "description": "Generate a financial chart. Returns a chart image that will be sent to Discord.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["comparison", "sector_heatmap", "earnings_history", "macro_trend"],
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
