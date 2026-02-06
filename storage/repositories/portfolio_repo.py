"""Portfolio holdings and financial profile repositories."""

import asyncpg
from typing import Any


class PortfolioRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_holdings(self, discord_id: int) -> list[dict[str, Any]]:
        """Get all holdings for a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT symbol, shares, cost_basis, acquired_date, account_type, notes, updated_at
                FROM portfolio_holdings
                WHERE discord_id = $1
                ORDER BY symbol
                """,
                discord_id,
            )
        return [dict(r) for r in rows]

    async def get_symbols(self, discord_id: int) -> list[str]:
        """Get just the symbols in a user's portfolio."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT symbol FROM portfolio_holdings WHERE discord_id = $1",
                discord_id,
            )
        return [r["symbol"] for r in rows]

    async def upsert(
        self,
        discord_id: int,
        symbol: str,
        shares: float,
        cost_basis: float | None = None,
        acquired_date: str | None = None,
        account_type: str = "taxable",
        notes: str | None = None,
    ) -> None:
        """Add or update a holding."""
        from datetime import date as date_type
        acq_date = None
        if acquired_date:
            try:
                acq_date = date_type.fromisoformat(acquired_date)
            except ValueError:
                pass

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO portfolio_holdings (discord_id, symbol, shares, cost_basis, acquired_date, account_type, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (discord_id, symbol, account_type) DO UPDATE SET
                    shares = $3,
                    cost_basis = COALESCE($4, portfolio_holdings.cost_basis),
                    acquired_date = COALESCE($5, portfolio_holdings.acquired_date),
                    notes = COALESCE($7, portfolio_holdings.notes),
                    updated_at = NOW()
                """,
                discord_id,
                symbol.upper(),
                shares,
                cost_basis,
                acq_date,
                account_type,
                notes,
            )

    async def remove(self, discord_id: int, symbol: str, account_type: str = "taxable") -> bool:
        """Remove a holding. Returns True if deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM portfolio_holdings WHERE discord_id = $1 AND symbol = $2 AND account_type = $3",
                discord_id,
                symbol.upper(),
                account_type,
            )
        return result.split()[-1] != "0"

    async def get_all_users_with_holdings(self) -> list[int]:
        """Get all discord_ids that have portfolio holdings."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT discord_id FROM portfolio_holdings"
            )
        return [r["discord_id"] for r in rows]

    async def get_all_held_symbols(self) -> set[str]:
        """Get all unique symbols held across all users."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT symbol FROM portfolio_holdings"
            )
        return {r["symbol"] for r in rows}


class FinancialProfileRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, discord_id: int) -> dict[str, Any] | None:
        """Get a user's financial profile."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM financial_profile WHERE discord_id = $1",
                discord_id,
            )
        return dict(row) if row else None

    async def upsert(
        self,
        discord_id: int,
        annual_income: float | None = None,
        investment_horizon: str | None = None,
        goals: list[str] | None = None,
        tax_bracket: str | None = None,
        monthly_investment: float | None = None,
    ) -> None:
        """Create or update a financial profile."""
        import json as json_mod
        goals_json = json_mod.dumps(goals) if goals else None

        async with self._pool.acquire() as conn:
            # Check if profile exists
            existing = await conn.fetchrow(
                "SELECT discord_id FROM financial_profile WHERE discord_id = $1", discord_id
            )
            if existing:
                # Update only provided fields
                updates = []
                params = [discord_id]
                idx = 2
                if annual_income is not None:
                    updates.append(f"annual_income = ${idx}")
                    params.append(annual_income)
                    idx += 1
                if investment_horizon is not None:
                    updates.append(f"investment_horizon = ${idx}")
                    params.append(investment_horizon)
                    idx += 1
                if goals_json is not None:
                    updates.append(f"goals = ${idx}::jsonb")
                    params.append(goals_json)
                    idx += 1
                if tax_bracket is not None:
                    updates.append(f"tax_bracket = ${idx}")
                    params.append(tax_bracket)
                    idx += 1
                if monthly_investment is not None:
                    updates.append(f"monthly_investment = ${idx}")
                    params.append(monthly_investment)
                    idx += 1
                if updates:
                    updates.append("updated_at = NOW()")
                    await conn.execute(
                        f"UPDATE financial_profile SET {', '.join(updates)} WHERE discord_id = $1",
                        *params,
                    )
            else:
                await conn.execute(
                    """
                    INSERT INTO financial_profile (discord_id, annual_income, investment_horizon, goals, tax_bracket, monthly_investment)
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6)
                    """,
                    discord_id,
                    annual_income,
                    investment_horizon,
                    goals_json or "[]",
                    tax_bracket,
                    monthly_investment,
                )
