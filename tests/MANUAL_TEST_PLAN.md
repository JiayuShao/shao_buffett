# Shao Buffett Manual Test Plan

Run these tests on Discord with the bot online. Each test lists the input, expected behavior, and what to verify.

## Test 1: Basic Chat — Price Check
**Input:** `@Shao Buffett what's AAPL at?`
**Expected:** Bot responds with Apple's current price, change, and change%. Should route to Haiku (routine query) and use the `get_quote` tool.

## Test 2: Chat — Multi-Tool Analysis
**Input:** `@Shao Buffett give me a full analysis of NVDA`
**Expected:** Bot uses multiple tools (fundamentals, analyst data, factor grades) and returns a detailed analysis. Should route to Sonnet. Response may take 10-20s due to tool calls. Look for the "thinking" indicator while it works.

## Test 3: Chat — Streaming + Tool Progress
**Input:** `@Shao Buffett compare MSFT and GOOGL — who's a better buy?`
**Expected:** Bot calls tools for both stocks (parallel execution), then streams back a comparative analysis. You should see text appearing progressively, not all at once.

## Test 4: Market Commands
**Input:** `/market overview`
**Expected:** Embed with market status (open/closed), key stock prices with green/red arrows, and top sector performance.

**Input:** `/market sector`
**Expected:** Embed listing all 11 sectors with percentage changes and directional arrows.

**Input:** `/market macro`
**Expected:** Embed with FRED macro indicators (GDP, CPI, unemployment, Fed funds rate, etc.) with latest values and dates.

## Test 5: News
**Input:** `/news latest`
**Expected:** Embed(s) with recent financial news articles, sources, and sentiment scores.

**Input:** `@Shao Buffett what's happening with TSLA?`
**Expected:** Bot uses `get_news` tool filtered by TSLA, returns recent headlines with sentiment context.

## Test 6: Portfolio — Add Holdings
**Input:** `@Shao Buffett I bought 50 shares of AAPL at $185`
**Expected:** Bot proactively calls `update_portfolio` (add, AAPL, 50 shares, $185 cost basis) AND `save_note` (decision note). Should confirm the position was saved.

**Input:** `@Shao Buffett I also have 100 MSFT at $420 in my Roth IRA`
**Expected:** Bot calls `update_portfolio` with `account_type: roth_ira`. Confirms saved.

## Test 7: Portfolio — View & Health
**Input:** `/portfolio show`
**Expected:** Embed listing your holdings (AAPL 50 shares @ $185, MSFT 100 shares @ $420) with account types.

**Input:** `@Shao Buffett how's my portfolio looking?`
**Expected:** Bot calls `get_portfolio_health` — returns aggregate quality score, sector concentration, weakest holdings, diversification assessment. Routes to Sonnet (portfolio-aware).

## Test 8: Notes — Cross-Conversation Memory
**Input:** `@Shao Buffett I'm worried about rising interest rates affecting my tech holdings`
**Expected:** Bot proactively calls `save_note` (type: concern, symbols: tech-related) without asking permission. Then responds with analysis.

**Input:** `/notes show`
**Expected:** Embed listing your saved notes — should include the concern from above plus any decision notes from Test 6.

**Input:** `/notes actions`
**Expected:** Shows open action items (if any were created during conversations).

## Test 9: Financial Profile
**Input:** `@Shao Buffett my income is $150k, I invest $2000/month, and I'm in the 24% tax bracket. My goal is retirement in 25 years.`
**Expected:** Bot proactively calls `update_financial_profile` with those details. Confirms saved. Does NOT ask for permission first.

**Input:** `/portfolio goals`
**Expected:** Shows your financial profile (income, monthly investment, tax bracket, goals, horizon).

## Test 10: Chart Generation
**Input:** `@Shao Buffett show me a price comparison chart for AAPL, MSFT, and GOOGL`
**Expected:** Bot calls `generate_chart` (type: comparison, symbols: [AAPL, MSFT, GOOGL]). A chart image is sent as a file attachment in Discord.

## Test 11: Deep Analysis (Opus)
**Input:** `@Shao Buffett give me a deep dive on whether NVDA is overvalued relative to its AI growth trajectory. Compare its valuation multiples to historical averages and factor in the latest earnings transcript.`
**Expected:** Routes to Opus (deep analysis keywords). Uses multiple tools: fundamentals, earnings, transcript, factor grades. Longer response with extended thinking. May take 30-60s.

## Test 12: Macro Data
**Input:** `@Shao Buffett what does the macro picture look like?`
**Expected:** Bot calls `get_macro_data` (snapshot). Returns FRED macro indicators (GDP, CPI, unemployment, Fed funds, yields, VIX).

## Test 13: Trending & Sentiment
**Input:** `@Shao Buffett what stocks are trending right now?`
**Expected:** Bot calls `get_trending_stocks`. Returns a ranked list of stocks by news volume with positive/negative sentiment breakdown.

**Input:** `@Shao Buffett compare the sentiment for AAPL vs TSLA over the past week`
**Expected:** Bot calls `get_sentiment` with both symbols. Returns daily sentiment time series.

## Test 14: Report Command
**Input:** `/report symbol:AAPL`
**Expected:** Generates a structured Opus-powered analyst report. Takes longer (Opus model). Should be a comprehensive, formatted report with multiple sections.

## Test 15: Context Retention
**Input (after Tests 6-9 above):** `@Shao Buffett based on what you know about me, what should I be watching this week?`
**Expected:** Bot's system prompt is enriched with your notes, portfolio, and financial profile. Response should reference your AAPL/MSFT holdings, your concern about interest rates, your retirement goal, and your tax situation — proving cross-conversation memory works.

## What to Watch For (All Tests)
- No error embeds (red) unless expected
- Bot defers properly (no "interaction failed" from Discord)
- Embeds use consistent colors (blue=info, green=bullish, red=bearish, purple=earnings/macro)
- Tool calls appear in logs (check terminal running the bot)
- Responses are coherent and use the data from tools (not hallucinated numbers)
