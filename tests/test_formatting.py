"""Tests for utils/formatting.py — number formatting and ticker validation."""

import pytest
from utils.formatting import (
    validate_ticker,
    format_currency,
    format_number,
    format_percent,
    format_change,
    format_large_number,
    truncate,
)


class TestValidateTicker:
    def test_valid_tickers(self):
        assert validate_ticker("AAPL") == "AAPL"
        assert validate_ticker("A") == "A"
        assert validate_ticker("MSFT") == "MSFT"
        assert validate_ticker("BRK") == "BRK"
        assert validate_ticker("NVDA") == "NVDA"

    def test_lowercase_normalized(self):
        assert validate_ticker("aapl") == "AAPL"
        assert validate_ticker("msft") == "MSFT"

    def test_with_whitespace(self):
        assert validate_ticker("  AAPL  ") == "AAPL"

    def test_too_long(self):
        assert validate_ticker("ABCDEF") is None

    def test_numbers_rejected(self):
        assert validate_ticker("A1") is None
        assert validate_ticker("123") is None

    def test_special_chars_rejected(self):
        assert validate_ticker("AA.B") is None
        assert validate_ticker("BRK-A") is None

    def test_empty_string(self):
        assert validate_ticker("") is None


class TestFormatCurrency:
    def test_trillions(self):
        assert format_currency(2_800_000_000_000) == "$2.80T"

    def test_billions(self):
        assert format_currency(150_000_000_000) == "$150.00B"

    def test_millions(self):
        assert format_currency(5_200_000) == "$5.20M"

    def test_normal(self):
        assert format_currency(185.50) == "$185.50"

    def test_small_number(self):
        assert format_currency(0.05) == "$0.05"

    def test_none(self):
        assert format_currency(None) == "N/A"

    def test_custom_decimals(self):
        assert format_currency(185.5, decimals=0) == "$186"

    def test_negative_billions(self):
        assert format_currency(-5_000_000_000) == "$-5.00B"


class TestFormatNumber:
    def test_basic(self):
        assert format_number(1234567.89) == "1,234,567.89"

    def test_none(self):
        assert format_number(None) == "N/A"

    def test_zero(self):
        assert format_number(0) == "0.00"


class TestFormatPercent:
    def test_positive(self):
        assert format_percent(5.25) == "+5.25%"

    def test_negative(self):
        assert format_percent(-3.14) == "-3.14%"

    def test_zero(self):
        assert format_percent(0) == "0.00%"

    def test_none(self):
        assert format_percent(None) == "N/A"


class TestFormatChange:
    def test_positive(self):
        result = format_change(2.50)
        assert "+2.50" in result
        assert "🟢" in result

    def test_negative(self):
        result = format_change(-1.75)
        assert "-1.75" in result
        assert "🔴" in result

    def test_zero(self):
        result = format_change(0)
        assert "⚪" in result

    def test_none(self):
        assert format_change(None) == "N/A"


class TestFormatLargeNumber:
    def test_trillions(self):
        assert format_large_number(2_500_000_000_000) == "2.5T"

    def test_billions(self):
        assert format_large_number(3_700_000_000) == "3.7B"

    def test_millions(self):
        assert format_large_number(15_000_000) == "15.0M"

    def test_thousands(self):
        assert format_large_number(50_000) == "50.0K"

    def test_small(self):
        assert format_large_number(42) == "42"

    def test_none(self):
        assert format_large_number(None) == "N/A"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", 100) == "hello"

    def test_long_text_truncated(self):
        text = "a" * 100
        result = truncate(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length(self):
        text = "a" * 100
        assert truncate(text, 100) == text

    def test_default_max(self):
        text = "a" * 2000
        result = truncate(text)
        assert len(result) == 1024
