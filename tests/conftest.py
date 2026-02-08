"""Shared test fixtures for Shao Buffett test suite."""

import os
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime, timezone

# Ensure settings can be imported without real env vars
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Database Pool Mock ──


class FakeRecord(dict):
    """Mimics asyncpg.Record: supports both dict-style and attribute access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class FakeConnection:
    """Mock asyncpg connection with configurable return values."""

    def __init__(self):
        self.execute_results: list[str] = ["DELETE 1"]
        self.fetch_results: list[list[dict]] = [[]]
        self.fetchrow_result: dict | None = None
        self.fetchval_result: int | None = 1
        self._execute_calls: list[tuple] = []
        self._fetch_calls: list[tuple] = []

    async def execute(self, query, *args):
        self._execute_calls.append((query, args))
        return self.execute_results[0] if self.execute_results else "UPDATE 0"

    async def fetch(self, query, *args):
        self._fetch_calls.append((query, args))
        result = self.fetch_results.pop(0) if self.fetch_results else []
        return [FakeRecord(r) for r in result]

    async def fetchrow(self, query, *args):
        return FakeRecord(self.fetchrow_result) if self.fetchrow_result else None

    async def fetchval(self, query, *args):
        return self.fetchval_result

    def transaction(self):
        return FakeTransaction()


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakePool:
    """Mock asyncpg.Pool that yields a FakeConnection."""

    def __init__(self):
        self.conn = FakeConnection()

    def acquire(self):
        return FakePoolContext(self.conn)


class FakePoolContext:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def fake_pool():
    """Provide a mock database pool."""
    return FakePool()


@pytest.fixture
def fake_conn(fake_pool):
    """Direct access to the underlying FakeConnection."""
    return fake_pool.conn


# ── Data Manager Mock ──


@pytest.fixture
def mock_data_manager():
    """Mock DataManager with all methods as AsyncMock."""
    dm = MagicMock()
    dm.get_quote = AsyncMock(return_value={
        "c": 185.50, "d": 2.30, "dp": 1.25,
        "h": 186.00, "l": 183.00, "o": 184.00, "pc": 183.20,
    })
    dm.get_company_profile = AsyncMock(return_value={
        "name": "Apple Inc.", "ticker": "AAPL", "sector": "Technology",
        "marketCapitalization": 2800000000000,
    })
    dm.get_fundamentals = AsyncMock(return_value={
        "metrics": {"peRatioTTM": 28.5}, "ratios": {"returnOnEquityTTM": 1.47},
    })
    dm.get_analyst_data = AsyncMock(return_value={
        "recommendations": [{"buy": 25, "hold": 8, "sell": 2}],
        "price_target": {"targetMean": 200.0},
        "upgrades_downgrades": [],
    })
    dm.get_earnings = AsyncMock(return_value=[
        {"date": "2025-01-30", "epsActual": 2.18, "epsEstimate": 2.10, "revenueActual": 124000000000},
    ])
    dm.get_news = AsyncMock(return_value=[
        {"title": "Apple hits record", "source": "Reuters", "sentiment": 0.7, "url": "https://example.com"},
    ])
    dm.get_macro_data = AsyncMock(return_value={
        "GDP": {"value": 27.36, "unit": "Trillions USD"},
        "FEDFUNDS": {"value": 5.33},
    })
    dm.get_sector_performance = AsyncMock(return_value=[
        {"sector": "Technology", "changesPercentage": "+2.5%"},
    ])
    dm.get_earnings_transcript = AsyncMock(return_value={
        "symbol": "AAPL", "quarter": 4, "year": 2024, "content": "Transcript content...",
    })
    dm.get_sec_filings = AsyncMock(return_value=[
        {"form_type": "10-K", "file_date": "2024-11-01", "entity_name": "Apple Inc."},
    ])
    dm.get_research_papers = AsyncMock(return_value=[
        {"title": "Deep Learning for Portfolio", "authors": ["Smith", "Jones"], "pdf_url": "https://arxiv.org/pdf/1234"},
    ])
    dm.get_polymarket = AsyncMock(return_value=[
        {"question": "Will the Fed cut rates?", "outcome_prices": "[0.65, 0.35]",
         "outcomes": '["Yes", "No"]', "volume": 1500000, "liquidity": 500000, "slug": "fed-rate-cut"},
    ])
    dm.get_news_for_sectors = AsyncMock(return_value=[
        {"title": "Tech sector surges", "source": "Reuters", "sentiment": 0.7,
         "url": "https://example.com/tech", "symbols": [], "description": "Tech rally continues"},
    ])
    dm.cache = MagicMock()
    dm.cache.cleanup = MagicMock(return_value=0)
    dm.cache.get = MagicMock(return_value=None)
    dm.cache.set = MagicMock()
    dm.start = AsyncMock()
    dm.close = AsyncMock()
    return dm


# ── Notification Dispatcher Mock ──


@pytest.fixture
def mock_dispatcher():
    """Mock NotificationDispatcher."""
    d = MagicMock()
    d.dispatch = AsyncMock(return_value=1)
    return d


# ── Timestamp helpers ──


@pytest.fixture
def now():
    """Current UTC datetime."""
    return datetime.now(UTC)


@pytest.fixture
def old_datetime():
    """Datetime 5 days ago (for stale action item tests)."""
    from datetime import timedelta
    return datetime.now(UTC) - timedelta(days=5)
