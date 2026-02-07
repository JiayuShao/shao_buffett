"""Analysis prompt templates."""


def stock_analysis_prompt(symbol: str, metrics: list[str] | None = None) -> str:
    """Generate a stock analysis prompt."""
    metric_str = ", ".join(metrics) if metrics else "PE, EPS growth, revenue growth, margins"
    return (
        f"Analyze {symbol} for me. Fetch the current quote, company profile, key fundamentals, "
        f"factor grades (get_factor_grades), analyst recommendations, and recent earnings. "
        f"Focus on these metrics: {metric_str}. "
        f"Also check for any recent news. Provide a concise analysis with:\n"
        f"- **Quant Rating** and factor grades prominently displayed\n"
        f"- Quant Rating vs Wall Street consensus — highlight any divergence\n"
        f"- Bull case and bear case with specific data points\n"
        f"- **Confidence Assessment**: Rate 1-10 with justification\n"
        f"- **Biggest Risk**: Single strongest argument against the thesis\n"
        f"- **Self-Critique**: What would change your view?"
    )


def comparison_prompt(symbols: list[str]) -> str:
    """Generate a stock comparison prompt."""
    tickers = ", ".join(symbols)
    return (
        f"Compare these stocks: {tickers}. For each, fetch the quote, key metrics, and analyst targets. "
        f"Create a comparison table and highlight key differences. Which offers the best value?"
    )


def earnings_analysis_prompt(symbol: str, year: int, quarter: int) -> str:
    """Generate an earnings analysis prompt."""
    return (
        f"Fetch the Q{quarter} {year} earnings transcript for {symbol} and analyze it. "
        f"Also get the latest earnings surprise data. Summarize the key takeaways, "
        f"management tone, guidance changes, and notable analyst questions."
    )


def macro_analysis_prompt() -> str:
    """Generate a macro analysis prompt."""
    return (
        "Give me a macro overview. Fetch the latest data for GDP, CPI, unemployment, "
        "Fed funds rate, 10Y yield, 2Y yield, VIX, and S&P 500. Analyze the current "
        "macro environment: is it risk-on or risk-off? What should investors watch?"
    )


def sector_analysis_prompt(sector: str | None = None) -> str:
    """Generate a sector analysis prompt."""
    if sector:
        return (
            f"Analyze the {sector} sector. Fetch sector performance data and identify "
            f"the key trends, top performers, and risks. How does it compare to the broader market?"
        )
    return (
        "Fetch sector performance data and give me an overview of all sectors. "
        "Which sectors are leading/lagging? What's driving the performance differences?"
    )


def deep_research_prompt(symbol: str) -> str:
    """Generate a deep research prompt (for Opus tier)."""
    return (
        f"Conduct an institutional-quality deep research analysis on {symbol}. "
        f"Fetch: 1) Company profile, 2) Full fundamentals and ratios, 3) Factor grades and Quant Rating "
        f"(get_factor_grades), 4) Analyst data and price targets, 5) Recent earnings data, "
        f"6) Latest news, 7) Recent SEC filings, 8) Technical indicators. "
        f"Synthesize all data into a comprehensive research note with: "
        f"Executive Summary (include Quant Rating prominently), Business Overview, "
        f"Factor Grade Analysis (all 5 grades with commentary), Financial Analysis, "
        f"Valuation Assessment, Quant vs Wall Street comparison, "
        f"Competitive Position, Risk Analysis, and Investment Conclusion with price target justification.\n\n"
        f"REQUIRED at the end of your analysis:\n"
        f"- **Confidence**: [1-10] with justification\n"
        f"- **Weakest Point**: Explicitly identify the weakest part of your thesis\n"
        f"- **Disconfirming Evidence**: What specific data did you find that argues AGAINST your conclusion?\n"
        f"- **Would Change My View If**: Specific, observable future conditions\n"
        f"- **Data Gaps**: What information was unavailable that would improve this analysis?"
    )
