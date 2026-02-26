"""Factor grade processor — computes quantitative ratings relative to sector peers."""

import asyncio
import structlog
from typing import Any
from data.manager import DataManager

log = structlog.get_logger(__name__)

# Grade thresholds: percentile → letter grade
GRADE_MAP = [
    (95, "A+"), (85, "A"), (75, "A-"),
    (65, "B+"), (55, "B"), (45, "B-"),
    (35, "C+"), (25, "C"), (15, "C-"),
    (8, "D+"), (3, "D"),
    (0, "F"),
]

# Quant rating labels
QUANT_LABELS = {
    5: "Strong Buy", 4: "Buy", 3: "Hold", 2: "Sell", 1: "Strong Sell",
}

# Sector peer lists (top liquid names per sector for peer comparison)
SECTOR_PEERS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "INTC", "CSCO", "QCOM", "TXN", "NOW"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN", "BMY", "GILD", "ISRG", "MDT", "CVS"],
    "Financial Services": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK", "AXP", "C", "SCHW", "CME", "ICE"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "MAR", "GM", "F", "ABNB", "ORLY", "CMG"],
    "Communication Services": ["GOOG", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "ATVI", "RBLX", "SPOT", "SNAP", "PINS"],
    "Industrials": ["CAT", "UNP", "HON", "UPS", "RTX", "BA", "DE", "LMT", "GE", "MMM", "ADP", "WM", "EMR", "ITW", "FDX"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ", "GIS", "KMB", "SYY", "KHC", "HSY", "STZ"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "PXD", "DVN", "HES", "HAL", "FANG", "BKR"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "ED", "WEC", "ES", "AWK", "DTE", "PPL", "FE"],
    "Real Estate": ["PLD", "AMT", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "DLR", "AVB", "EQR", "VTR", "ARE", "MAA", "UDR"],
    "Basic Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DD", "DOW", "PPG", "VMC", "MLM", "CF", "MOS", "ALB"],
}


def _percentile_to_grade(percentile: float) -> str:
    """Convert a percentile (0-100) to a letter grade."""
    for threshold, grade in GRADE_MAP:
        if percentile >= threshold:
            return grade
    return "F"


def _grade_to_score(grade: str) -> float:
    """Convert letter grade to numeric score (1.0-5.0)."""
    grade_scores = {
        "A+": 5.0, "A": 4.7, "A-": 4.3,
        "B+": 4.0, "B": 3.7, "B-": 3.3,
        "C+": 3.0, "C": 2.7, "C-": 2.3,
        "D+": 2.0, "D": 1.7,
        "F": 1.0,
    }
    return grade_scores.get(grade, 2.5)


def _compute_percentile(value: float, peer_values: list[float], higher_is_better: bool = True) -> float:
    """Compute where a value ranks among peers (0-100 percentile)."""
    if not peer_values:
        return 50.0
    below = sum(1 for v in peer_values if v < value)
    equal = sum(1 for v in peer_values if v == value)
    percentile = ((below + 0.5 * equal) / len(peer_values)) * 100
    if not higher_is_better:
        percentile = 100 - percentile
    return percentile


class FactorGradeProcessor:
    """Computes factor grades and quant ratings for stocks relative to sector peers."""

    def __init__(self, data_manager: DataManager) -> None:
        self.dm = data_manager

    async def get_factor_grades(self, symbol: str) -> dict[str, Any]:
        """Compute factor grades and quant rating for a symbol."""
        # Get company sector
        profile = await self.dm.get_company_profile(symbol)
        sector = profile.get("sector", "Technology")

        # Get target stock data
        fundamentals = await self.dm.get_fundamentals(symbol)
        quote = await self.dm.get_quote(symbol)
        analyst = await self.dm.get_analyst_data(symbol)
        earnings = await self.dm.get_earnings(symbol)

        # Get historical prices for momentum
        try:
            hist_prices = await self.dm.get_historical_prices(symbol, limit=260)
        except Exception:
            hist_prices = []

        # Get peer data
        peer_symbols = await self._get_peers(symbol, sector)
        peer_data = await self._fetch_peer_data(peer_symbols)

        # Compute each factor
        value_grade, value_details = self._compute_value_grade(fundamentals, peer_data)
        growth_grade, growth_details = self._compute_growth_grade(fundamentals, peer_data)
        profit_grade, profit_details = self._compute_profitability_grade(fundamentals, peer_data)
        momentum_grade, momentum_details = self._compute_momentum_grade(quote, hist_prices, peer_data)
        eps_grade, eps_details = self._compute_eps_revision_grade(analyst, earnings, peer_data)

        # Composite quant rating (weighted average)
        factor_scores = {
            "value": _grade_to_score(value_grade),
            "growth": _grade_to_score(growth_grade),
            "profitability": _grade_to_score(profit_grade),
            "momentum": _grade_to_score(momentum_grade),
            "eps_revisions": _grade_to_score(eps_grade),
        }
        # Weights: equal for now, can be tuned
        composite = sum(factor_scores.values()) / len(factor_scores)
        quant_label = self._score_to_label(composite)

        return {
            "symbol": symbol,
            "sector": sector,
            "quant_rating": round(composite, 2),
            "quant_label": quant_label,
            "factor_grades": {
                "value": value_grade,
                "growth": growth_grade,
                "profitability": profit_grade,
                "momentum": momentum_grade,
                "eps_revisions": eps_grade,
            },
            "factor_details": {
                "value": value_details,
                "growth": growth_details,
                "profitability": profit_details,
                "momentum": momentum_details,
                "eps_revisions": eps_details,
            },
            "peer_count": len(peer_data),
        }

    async def get_portfolio_health(self, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute portfolio-level health metrics from holdings."""
        # Fetch grades for all holdings in parallel
        grades_tasks = [self.get_factor_grades(h["symbol"]) for h in holdings]
        results = await asyncio.gather(*grades_tasks, return_exceptions=True)

        holding_grades = []
        sector_weights: dict[str, float] = {}
        total_value = 0.0
        weakest = []
        strongest = []

        for holding, result in zip(holdings, results):
            if isinstance(result, Exception):
                log.warning("portfolio_health_grade_error", symbol=holding["symbol"], error=str(result))
                continue

            shares = float(holding.get("shares", 0))
            cost = float(holding.get("cost_basis", 0))
            position_value = shares * cost if cost > 0 else shares * 100  # Estimate if no cost basis
            total_value += position_value

            entry = {
                "symbol": holding["symbol"],
                "shares": shares,
                "position_value": position_value,
                "quant_rating": result["quant_rating"],
                "quant_label": result["quant_label"],
                "factor_grades": result["factor_grades"],
                "sector": result["sector"],
            }
            holding_grades.append(entry)

            # Track sector concentration
            sec = result["sector"]
            sector_weights[sec] = sector_weights.get(sec, 0) + position_value

        if not holding_grades:
            return {"error": "Could not compute grades for any holdings"}

        # Compute weighted quality score
        if total_value > 0:
            weighted_score = sum(
                h["quant_rating"] * h["position_value"] / total_value
                for h in holding_grades
            )
        else:
            weighted_score = sum(h["quant_rating"] for h in holding_grades) / len(holding_grades)

        # Sector concentration (Herfindahl index)
        if total_value > 0:
            sector_pcts = {s: (v / total_value) * 100 for s, v in sector_weights.items()}
            herfindahl = sum((pct / 100) ** 2 for pct in sector_pcts.values())
        else:
            sector_pcts = {}
            herfindahl = 1.0

        # Identify weakest and strongest
        sorted_by_rating = sorted(holding_grades, key=lambda h: h["quant_rating"])
        weakest = [
            {"symbol": h["symbol"], "rating": h["quant_rating"], "label": h["quant_label"]}
            for h in sorted_by_rating[:3] if h["quant_rating"] < 3.0
        ]
        strongest = [
            {"symbol": h["symbol"], "rating": h["quant_rating"], "label": h["quant_label"]}
            for h in sorted_by_rating[-3:] if h["quant_rating"] >= 3.5
        ]

        # Diversification assessment
        num_sectors = len(sector_pcts)
        max_sector_pct = max(sector_pcts.values()) if sector_pcts else 100
        if herfindahl > 0.4:
            diversification = "Poor"
        elif herfindahl > 0.25:
            diversification = "Fair"
        elif herfindahl > 0.15:
            diversification = "Good"
        else:
            diversification = "Excellent"

        return {
            "portfolio_score": round(weighted_score, 2),
            "portfolio_label": self._score_to_label(weighted_score),
            "num_holdings": len(holding_grades),
            "total_estimated_value": round(total_value, 2),
            "sector_allocation": {s: round(p, 1) for s, p in sorted(sector_pcts.items(), key=lambda x: -x[1])},
            "diversification": diversification,
            "herfindahl_index": round(herfindahl, 4),
            "top_sector": max(sector_pcts, key=sector_pcts.get) if sector_pcts else "N/A",
            "top_sector_pct": round(max_sector_pct, 1) if sector_pcts else 0,
            "weakest_holdings": weakest,
            "strongest_holdings": strongest,
            "holdings_detail": [
                {
                    "symbol": h["symbol"],
                    "quant_rating": h["quant_rating"],
                    "quant_label": h["quant_label"],
                    "grades": h["factor_grades"],
                    "sector": h["sector"],
                }
                for h in sorted(holding_grades, key=lambda x: -x["quant_rating"])
            ],
        }

    # ── Peer data fetching ──

    async def _get_peers(self, symbol: str, sector: str) -> list[str]:
        """Get peer symbols for comparison."""
        # Try FMP peer list first
        try:
            fmp_peers = await self.dm.fmp.get_stock_peers(symbol)
            if fmp_peers and len(fmp_peers) >= 5:
                return [p for p in fmp_peers[:15] if p != symbol]
        except Exception:
            pass

        # Fall back to hardcoded sector peers
        peers = SECTOR_PEERS.get(sector, SECTOR_PEERS["Technology"])
        return [p for p in peers if p != symbol]

    async def _fetch_peer_data(self, peer_symbols: list[str]) -> list[dict[str, Any]]:
        """Fetch fundamentals for peer symbols (best effort, parallel)."""
        async def _safe_fetch(symbol: str) -> dict[str, Any] | None:
            try:
                fundamentals = await self.dm.get_fundamentals(symbol)
                quote = await self.dm.get_quote(symbol)
                analyst = await self.dm.get_analyst_data(symbol)
                return {"symbol": symbol, "fundamentals": fundamentals, "quote": quote, "analyst": analyst}
            except Exception:
                return None

        results = await asyncio.gather(*[_safe_fetch(s) for s in peer_symbols[:12]])
        return [r for r in results if r is not None]

    # ── Factor computation ──

    def _compute_value_grade(
        self, fundamentals: dict[str, Any], peer_data: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        """Compute Value factor grade from valuation multiples (lower is better)."""
        metrics = fundamentals.get("metrics", {})
        ratios = fundamentals.get("ratios", {})

        pe = metrics.get("peRatio") or ratios.get("priceEarningsRatio")
        pb = metrics.get("pbRatio") or ratios.get("priceToBookRatio")
        ps = metrics.get("priceToSalesRatio") or ratios.get("priceToSalesRatio")
        ev_ebitda = metrics.get("enterpriseValueOverEBITDA") or ratios.get("enterpriseValueMultiple")

        peer_pes = self._extract_peer_metric(peer_data, "peRatio", "priceEarningsRatio")
        peer_pbs = self._extract_peer_metric(peer_data, "pbRatio", "priceToBookRatio")
        peer_pss = self._extract_peer_metric(peer_data, "priceToSalesRatio", "priceToSalesRatio")

        percentiles = []
        details = {}

        if pe and pe > 0:
            pct = _compute_percentile(pe, peer_pes, higher_is_better=False)
            percentiles.append(pct)
            details["pe_ratio"] = round(pe, 2)
            details["pe_percentile"] = round(pct, 0)

        if pb and pb > 0:
            pct = _compute_percentile(pb, peer_pbs, higher_is_better=False)
            percentiles.append(pct)
            details["pb_ratio"] = round(pb, 2)

        if ps and ps > 0:
            pct = _compute_percentile(ps, peer_pss, higher_is_better=False)
            percentiles.append(pct)
            details["ps_ratio"] = round(ps, 2)

        if ev_ebitda and ev_ebitda > 0:
            details["ev_ebitda"] = round(ev_ebitda, 2)

        avg_pct = sum(percentiles) / len(percentiles) if percentiles else 50.0
        grade = _percentile_to_grade(avg_pct)
        details["composite_percentile"] = round(avg_pct, 0)
        return grade, details

    def _compute_growth_grade(
        self, fundamentals: dict[str, Any], peer_data: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        """Compute Growth factor grade from revenue/earnings growth."""
        metrics = fundamentals.get("metrics", {})
        ratios = fundamentals.get("ratios", {})

        rev_growth = metrics.get("revenueGrowth") or ratios.get("revenueGrowth")
        eps_growth = metrics.get("epsgrowth") or ratios.get("epsgrowth")
        net_income_growth = metrics.get("netIncomeGrowth") or ratios.get("netIncomeGrowth")

        peer_rev = self._extract_peer_metric(peer_data, "revenueGrowth", "revenueGrowth")
        peer_eps = self._extract_peer_metric(peer_data, "epsgrowth", "epsgrowth")

        percentiles = []
        details = {}

        if rev_growth is not None:
            pct = _compute_percentile(rev_growth, peer_rev)
            percentiles.append(pct)
            details["revenue_growth"] = f"{rev_growth * 100:.1f}%" if abs(rev_growth) < 10 else f"{rev_growth:.1f}%"

        if eps_growth is not None:
            pct = _compute_percentile(eps_growth, peer_eps)
            percentiles.append(pct)
            details["eps_growth"] = f"{eps_growth * 100:.1f}%" if abs(eps_growth) < 10 else f"{eps_growth:.1f}%"

        if net_income_growth is not None:
            details["net_income_growth"] = f"{net_income_growth * 100:.1f}%" if abs(net_income_growth) < 10 else f"{net_income_growth:.1f}%"

        avg_pct = sum(percentiles) / len(percentiles) if percentiles else 50.0
        grade = _percentile_to_grade(avg_pct)
        details["composite_percentile"] = round(avg_pct, 0)
        return grade, details

    def _compute_profitability_grade(
        self, fundamentals: dict[str, Any], peer_data: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        """Compute Profitability factor grade from margins and returns."""
        metrics = fundamentals.get("metrics", {})
        ratios = fundamentals.get("ratios", {})

        gross_margin = ratios.get("grossProfitMargin")
        op_margin = ratios.get("operatingProfitMargin")
        net_margin = ratios.get("netProfitMargin")
        roe = metrics.get("roe") or ratios.get("returnOnEquity")
        roa = metrics.get("roic") or ratios.get("returnOnAssets")

        peer_gm = self._extract_peer_ratio(peer_data, "grossProfitMargin")
        peer_om = self._extract_peer_ratio(peer_data, "operatingProfitMargin")
        peer_nm = self._extract_peer_ratio(peer_data, "netProfitMargin")
        peer_roe = self._extract_peer_metric(peer_data, "roe", "returnOnEquity")

        percentiles = []
        details = {}

        if gross_margin is not None:
            pct = _compute_percentile(gross_margin, peer_gm)
            percentiles.append(pct)
            details["gross_margin"] = f"{gross_margin * 100:.1f}%" if abs(gross_margin) < 1 else f"{gross_margin:.1f}%"

        if op_margin is not None:
            pct = _compute_percentile(op_margin, peer_om)
            percentiles.append(pct)
            details["operating_margin"] = f"{op_margin * 100:.1f}%" if abs(op_margin) < 1 else f"{op_margin:.1f}%"

        if net_margin is not None:
            pct = _compute_percentile(net_margin, peer_nm)
            percentiles.append(pct)
            details["net_margin"] = f"{net_margin * 100:.1f}%" if abs(net_margin) < 1 else f"{net_margin:.1f}%"

        if roe is not None:
            pct = _compute_percentile(roe, peer_roe)
            percentiles.append(pct)
            details["roe"] = f"{roe * 100:.1f}%" if abs(roe) < 1 else f"{roe:.1f}%"

        avg_pct = sum(percentiles) / len(percentiles) if percentiles else 50.0
        grade = _percentile_to_grade(avg_pct)
        details["composite_percentile"] = round(avg_pct, 0)
        return grade, details

    def _compute_momentum_grade(
        self, quote: dict[str, Any], hist_prices: list[dict[str, Any]], peer_data: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        """Compute Momentum factor grade from price performance over multiple periods."""
        details = {}
        percentiles = []

        # Calculate returns from historical prices
        if hist_prices and len(hist_prices) > 20:
            current = hist_prices[0].get("close", 0)
            returns = {}

            if len(hist_prices) > 21 and current > 0:
                m1_price = hist_prices[21].get("close", current)
                returns["1m"] = (current - m1_price) / m1_price if m1_price > 0 else 0

            if len(hist_prices) > 63 and current > 0:
                m3_price = hist_prices[63].get("close", current)
                returns["3m"] = (current - m3_price) / m3_price if m3_price > 0 else 0

            if len(hist_prices) > 126 and current > 0:
                m6_price = hist_prices[126].get("close", current)
                returns["6m"] = (current - m6_price) / m6_price if m6_price > 0 else 0

            if len(hist_prices) > 252 and current > 0:
                y1_price = hist_prices[252].get("close", current)
                returns["12m"] = (current - y1_price) / y1_price if y1_price > 0 else 0

            for period, ret in returns.items():
                details[f"return_{period}"] = f"{ret * 100:+.1f}%"

            # Use 6-month return as primary (most commonly used momentum factor)
            if "6m" in returns:
                # Simple percentile estimate: positive = above 50, scale by magnitude
                pct = 50 + returns["6m"] * 200  # Rough scaling
                pct = max(0, min(100, pct))
                percentiles.append(pct)

            if "3m" in returns:
                pct = 50 + returns["3m"] * 300
                pct = max(0, min(100, pct))
                percentiles.append(pct)
        else:
            # Fall back to daily change
            change_pct = quote.get("dp", quote.get("changesPercentage", quote.get("change_pct", 0)))
            if change_pct:
                details["daily_change"] = f"{float(change_pct):+.1f}%"

        avg_pct = sum(percentiles) / len(percentiles) if percentiles else 50.0
        grade = _percentile_to_grade(avg_pct)
        details["composite_percentile"] = round(avg_pct, 0)
        return grade, details

    def _compute_eps_revision_grade(
        self, analyst: dict[str, Any], earnings: list | dict, peer_data: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any]]:
        """Compute EPS Revisions factor grade from analyst estimate changes and earnings surprises."""
        details = {}
        signals = []

        # Look at analyst recommendations trend
        recs = analyst.get("recommendations", [])
        if recs and len(recs) >= 2:
            latest = recs[0]
            prev = recs[1]
            buy_now = latest.get("buy", 0) + latest.get("strongBuy", 0)
            buy_prev = prev.get("buy", 0) + prev.get("strongBuy", 0)
            sell_now = latest.get("sell", 0) + latest.get("strongSell", 0)
            sell_prev = prev.get("sell", 0) + prev.get("strongSell", 0)

            buy_change = buy_now - buy_prev
            sell_change = sell_now - sell_prev

            if buy_change > 0 and sell_change <= 0:
                signals.append(80)  # Positive revisions
                details["analyst_trend"] = f"Buy recs increased by {buy_change}"
            elif sell_change > 0 and buy_change <= 0:
                signals.append(20)  # Negative revisions
                details["analyst_trend"] = f"Sell recs increased by {sell_change}"
            else:
                signals.append(50)
                details["analyst_trend"] = "Mixed"

        # Look at recent earnings surprises
        if isinstance(earnings, list) and earnings:
            surprises = []
            for e in earnings[:4]:
                actual = e.get("actual")
                estimate = e.get("estimate")
                if actual is not None and estimate is not None and estimate != 0:
                    surprise_pct = ((actual - estimate) / abs(estimate)) * 100
                    surprises.append(surprise_pct)

            if surprises:
                avg_surprise = sum(surprises) / len(surprises)
                details["avg_earnings_surprise"] = f"{avg_surprise:+.1f}%"
                details["last_4q_beats"] = sum(1 for s in surprises if s > 0)

                # Map surprise to percentile
                if avg_surprise > 10:
                    signals.append(90)
                elif avg_surprise > 5:
                    signals.append(75)
                elif avg_surprise > 0:
                    signals.append(60)
                elif avg_surprise > -5:
                    signals.append(40)
                else:
                    signals.append(15)

        # Estimate changes from analyst estimates
        estimates = analyst.get("estimates", [])
        if estimates and len(estimates) >= 1:
            latest_est = estimates[0]
            est_eps = latest_est.get("epsAvg") or latest_est.get("estimatedEpsAvg")
            if est_eps is not None:
                details["fwd_eps_estimate"] = round(est_eps, 2)

        avg_pct = sum(signals) / len(signals) if signals else 50.0
        grade = _percentile_to_grade(avg_pct)
        details["composite_percentile"] = round(avg_pct, 0)
        return grade, details

    # ── Helper methods ──

    @staticmethod
    def _extract_peer_metric(
        peer_data: list[dict[str, Any]], metrics_key: str, ratios_key: str
    ) -> list[float]:
        """Extract a metric from peer fundamentals data."""
        values = []
        for p in peer_data:
            fund = p.get("fundamentals", {})
            val = (
                fund.get("metrics", {}).get(metrics_key)
                or fund.get("ratios", {}).get(ratios_key)
            )
            if val is not None and isinstance(val, (int, float)) and val != 0:
                values.append(float(val))
        return values

    @staticmethod
    def _extract_peer_ratio(peer_data: list[dict[str, Any]], ratio_key: str) -> list[float]:
        """Extract a ratio from peer fundamentals data."""
        values = []
        for p in peer_data:
            fund = p.get("fundamentals", {})
            val = fund.get("ratios", {}).get(ratio_key)
            if val is not None and isinstance(val, (int, float)):
                values.append(float(val))
        return values

    @staticmethod
    def _score_to_label(score: float) -> str:
        """Convert composite score to quant label."""
        if score >= 4.5:
            return "Strong Buy"
        elif score >= 3.5:
            return "Buy"
        elif score >= 2.5:
            return "Hold"
        elif score >= 1.5:
            return "Sell"
        return "Strong Sell"
