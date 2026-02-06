"""Tests for SQL migration files — verify structure and syntax."""

import pytest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).parent.parent / "storage" / "migrations"


class TestMigrationFiles:
    def test_migrations_exist(self):
        assert MIGRATIONS_DIR.exists()
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        assert len(sql_files) >= 4

    def test_migrations_ordered(self):
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        names = [f.name for f in sql_files]
        assert names[0].startswith("001_")
        assert names[1].startswith("002_")
        assert names[2].startswith("003_")
        assert names[3].startswith("004_")


class TestMigration002:
    def _read(self):
        return (MIGRATIONS_DIR / "002_notes_and_memory.sql").read_text()

    def test_creates_conversation_notes(self):
        sql = self._read()
        assert "CREATE TABLE" in sql
        assert "conversation_notes" in sql

    def test_has_required_columns(self):
        sql = self._read()
        assert "discord_id" in sql
        assert "note_type" in sql
        assert "content" in sql
        assert "symbols" in sql
        assert "is_resolved" in sql
        assert "created_at" in sql
        assert "expires_at" in sql

    def test_note_type_check_constraint(self):
        sql = self._read()
        assert "insight" in sql
        assert "decision" in sql
        assert "action_item" in sql
        assert "preference" in sql
        assert "concern" in sql

    def test_gin_index_on_symbols(self):
        sql = self._read()
        assert "GIN" in sql
        assert "symbols" in sql


class TestMigration003:
    def _read(self):
        return (MIGRATIONS_DIR / "003_portfolio.sql").read_text()

    def test_creates_portfolio_holdings(self):
        sql = self._read()
        assert "portfolio_holdings" in sql

    def test_creates_financial_profile(self):
        sql = self._read()
        assert "financial_profile" in sql

    def test_portfolio_has_required_columns(self):
        sql = self._read()
        assert "discord_id" in sql
        assert "symbol" in sql
        assert "shares" in sql
        assert "cost_basis" in sql
        assert "account_type" in sql

    def test_account_type_constraint(self):
        sql = self._read()
        assert "taxable" in sql
        assert "ira" in sql
        assert "roth_ira" in sql
        assert "401k" in sql

    def test_unique_constraint(self):
        sql = self._read()
        assert "UNIQUE" in sql

    def test_financial_profile_columns(self):
        sql = self._read()
        assert "annual_income" in sql
        assert "investment_horizon" in sql
        assert "goals" in sql
        assert "tax_bracket" in sql
        assert "monthly_investment" in sql


class TestMigration004:
    def _read(self):
        return (MIGRATIONS_DIR / "004_user_activity.sql").read_text()

    def test_creates_user_activity(self):
        sql = self._read()
        assert "user_activity" in sql

    def test_creates_proactive_insights(self):
        sql = self._read()
        assert "proactive_insights" in sql

    def test_user_activity_columns(self):
        sql = self._read()
        assert "query_type" in sql
        assert "symbols" in sql

    def test_proactive_insight_types(self):
        sql = self._read()
        assert "portfolio_drift" in sql
        assert "earnings_upcoming" in sql
        assert "price_movement" in sql
        assert "news_relevant" in sql
        assert "action_reminder" in sql
        assert "symbol_suggestion" in sql

    def test_gin_index_on_activity_symbols(self):
        sql = self._read()
        assert "GIN" in sql

    def test_undelivered_index(self):
        sql = self._read()
        assert "is_delivered" in sql
