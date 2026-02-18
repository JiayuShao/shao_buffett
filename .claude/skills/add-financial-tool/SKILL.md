---
name: add-financial-tool
description: Add a new AI tool that Claude can call during conversations. Covers the 3-file workflow (tools.py → engine.py → data/manager.py) with all gotchas.
---

# Add a Financial Tool

New AI tools follow a 3-file pattern. All three must be updated for the tool to work.

## Step 1: Define the tool schema in `ai/tools.py`

Add a new dict to the `FINANCIAL_TOOLS` list. The tool description is critical — it drives Claude's tool selection.

```python
# In FINANCIAL_TOOLS list:
{
    "name": "get_options_chain",
    "description": (
        "Get options chain data for a stock: calls and puts with strike prices, premiums, "
        "volume, open interest, and implied volatility. Use when the user asks about options, "
        "'what are the calls on X?', or for volatility analysis. NOT for stock prices — use "
        "get_quote for that."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock ticker symbol",
            },
            "expiration": {
                "type": "string",
                "description": "Expiration date (YYYY-MM-DD). Omit for nearest expiry.",
            },
        },
        "required": ["symbol"],
    },
},
```

### Tool description guidelines
- Start with what it returns, not what it does
- Include example user phrases that should trigger this tool ("use when...")
- State what it is NOT for, pointing to the correct alternative tool
- Be specific enough that Claude picks the right tool — vague descriptions cause mis-routing

### If Haiku should have access
Add the tool name to `ROUTINE_TOOL_NAMES` at the bottom of `ai/tools.py`:

```python
ROUTINE_TOOL_NAMES = {
    "get_quote", "get_company_profile", "get_news", "get_trending_stocks",
    "save_note", "get_user_notes",
    "get_options_chain",  # <-- add here
}
```

Only add to `ROUTINE_TOOL_NAMES` if the tool is commonly needed for simple/routine queries. Most financial data tools should NOT be added (Haiku gets 6 tools to save ~1.5K tokens/request).

## Step 2: Add match case in `ai/engine.py`

In the `_execute_tool` method, add a `case` branch inside the `match tool_name:` block:

```python
case "get_options_chain":
    return await self.data_manager.get_options_chain(
        symbol=tool_input["symbol"],
        expiration=tool_input.get("expiration"),
    )
```

### Gotchas
- **Never raise exceptions** — return `{"error": "..."}` dict instead. The outer try/except handles this, but if you do additional validation, return an error dict.
- **Personal tools need `user_id`**: if the tool accesses user-specific data (notes, portfolio), check `if not user_id: return {"error": "No user context"}` first.
- **`send_file`** is available for tools that generate files (charts). Access via the `send_file` parameter.
- Tool results are automatically capped at `MAX_TOOL_RESULT_CHARS = 12_000` chars (~3K tokens). Large results (transcripts, filings) get truncated.
- Tools requested in the same round run in parallel via `asyncio.gather()` — make sure your tool is safe for concurrent execution.

## Step 3: Implement the data method in `data/manager.py`

Add a method on `DataManager` that fetches and caches the data:

```python
async def get_options_chain(
    self, symbol: str, expiration: str | None = None
) -> dict[str, Any]:
    """Get options chain for a stock."""
    key = f"options:{symbol}:{expiration or 'nearest'}"
    cached = self.cache.get(key)
    if cached:
        return cached
    data = await self.fmp.get_options_chain(symbol, expiration=expiration)
    self.cache.set(key, data, CACHE_TTL["fundamentals"])  # Pick appropriate TTL
    return data
```

### Cache TTL reference (from `config/constants.py`)
| Key | TTL | Use for |
|-----|-----|---------|
| `quote` | 60s | Real-time prices |
| `news` | 120s | News, sentiment, trending |
| `fundamentals` | 1h | Financial metrics, options |
| `analyst` | 2h | Analyst data, insider trades |
| `macro` | 30min | Macro indicators, technicals |
| `profile` | 1 day | Company profiles |
| `transcript` | 1 day | Earnings transcripts |
| `filing` | 1 day | SEC filings |

### If using a new collector
If the data comes from a new API, create a collector first (see the `add-data-collector` skill). Otherwise, call existing collectors: `self.finnhub`, `self.fmp`, `self.marketaux`, `self.fred`, `self.sec_edgar`, `self.arxiv`.

## Checklist

- [ ] Tool schema in `ai/tools.py` with specific description
- [ ] Match case in `ai/engine.py` `_execute_tool()`
- [ ] Data method in `data/manager.py` with caching
- [ ] Considered whether to add to `ROUTINE_TOOL_NAMES`
- [ ] Tool returns dicts/lists (not raw strings)
- [ ] No exceptions raised from tool — errors returned as `{"error": "..."}`
