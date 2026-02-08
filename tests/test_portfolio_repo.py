"""Tests for storage/repositories/portfolio_repo.py — portfolio CRUD."""

import pytest
from datetime import UTC, datetime
from storage.repositories.portfolio_repo import PortfolioRepository, FinancialProfileRepository


class TestPortfolioRepository:
    @pytest.fixture
    def repo(self, fake_pool):
        return PortfolioRepository(fake_pool)

    async def test_get_holdings(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"symbol": "AAPL", "shares": 100, "cost_basis": 185.0, "acquired_date": None,
             "account_type": "taxable", "notes": None, "updated_at": datetime.now(UTC)},
            {"symbol": "MSFT", "shares": 50, "cost_basis": 380.0, "acquired_date": None,
             "account_type": "ira", "notes": "Long term hold", "updated_at": datetime.now(UTC)},
        ]]
        holdings = await repo.get_holdings(12345)
        assert len(holdings) == 2
        assert holdings[0]["symbol"] == "AAPL"
        assert holdings[1]["shares"] == 50

    async def test_get_holdings_empty(self, repo, fake_conn):
        fake_conn.fetch_results = [[]]
        holdings = await repo.get_holdings(12345)
        assert holdings == []

    async def test_get_symbols(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"symbol": "AAPL"},
            {"symbol": "MSFT"},
        ]]
        symbols = await repo.get_symbols(12345)
        assert symbols == ["AAPL", "MSFT"]

    async def test_upsert_basic(self, repo, fake_conn):
        await repo.upsert(discord_id=12345, symbol="aapl", shares=100, cost_basis=185.0)
        assert len(fake_conn._execute_calls) == 1
        query, args = fake_conn._execute_calls[0]
        assert "INSERT INTO portfolio_holdings" in query
        # Symbol should be uppercased
        assert args[1] == "AAPL"
        assert args[2] == 100

    async def test_upsert_with_acquired_date(self, repo, fake_conn):
        await repo.upsert(discord_id=12345, symbol="TSLA", shares=50,
                          acquired_date="2024-06-15", account_type="roth_ira")
        assert len(fake_conn._execute_calls) == 1
        query, args = fake_conn._execute_calls[0]
        assert args[5] == "roth_ira"

    async def test_upsert_invalid_date_ignores(self, repo, fake_conn):
        # Invalid date should not raise
        await repo.upsert(discord_id=12345, symbol="NVDA", shares=25, acquired_date="not-a-date")
        assert len(fake_conn._execute_calls) == 1

    async def test_remove_success(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 1"]
        removed = await repo.remove(12345, "aapl")
        assert removed is True

    async def test_remove_not_found(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 0"]
        removed = await repo.remove(12345, "XYZ")
        assert removed is False

    async def test_get_all_users_with_holdings(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"discord_id": 111},
            {"discord_id": 222},
        ]]
        users = await repo.get_all_users_with_holdings()
        assert users == [111, 222]

    async def test_get_all_held_symbols(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"symbol": "AAPL"},
            {"symbol": "NVDA"},
        ]]
        symbols = await repo.get_all_held_symbols()
        assert symbols == {"AAPL", "NVDA"}


class TestFinancialProfileRepository:
    @pytest.fixture
    def repo(self, fake_pool):
        return FinancialProfileRepository(fake_pool)

    async def test_get_existing(self, repo, fake_conn):
        fake_conn.fetchrow_result = {
            "discord_id": 12345, "annual_income": 150000,
            "investment_horizon": "10+ years", "goals": ["retirement"],
            "tax_bracket": "24%", "monthly_investment": 2000,
        }
        profile = await repo.get(12345)
        assert profile is not None
        assert profile["annual_income"] == 150000

    async def test_get_nonexistent(self, repo, fake_conn):
        fake_conn.fetchrow_result = None
        profile = await repo.get(12345)
        assert profile is None

    async def test_upsert_new_profile(self, repo, fake_conn):
        # No existing profile
        fake_conn.fetchrow_result = None
        await repo.upsert(
            discord_id=12345,
            annual_income=150000,
            investment_horizon="10+ years",
            goals=["retirement", "house"],
            tax_bracket="24%",
        )
        assert len(fake_conn._execute_calls) == 1
        query, _ = fake_conn._execute_calls[0]
        assert "INSERT INTO financial_profile" in query

    async def test_upsert_update_existing(self, repo, fake_conn):
        # Existing profile found
        fake_conn.fetchrow_result = {"discord_id": 12345}
        await repo.upsert(
            discord_id=12345,
            annual_income=200000,
        )
        assert len(fake_conn._execute_calls) == 1
        query, _ = fake_conn._execute_calls[0]
        assert "UPDATE financial_profile" in query
        assert "annual_income" in query

    async def test_upsert_no_fields_does_nothing(self, repo, fake_conn):
        fake_conn.fetchrow_result = {"discord_id": 12345}
        await repo.upsert(discord_id=12345)
        # No update query should be issued (only the fetchrow for check)
        assert len(fake_conn._execute_calls) == 0
