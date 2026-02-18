"""Tests for ai/prompts/ — system prompts and templates."""

import pytest
from ai.prompts.system import (
    BASE_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    BRIEFING_SYSTEM_PROMPT,
    CLASSIFICATION_SYSTEM_PROMPT,
    TRANSCRIPT_SUMMARY_PROMPT,
    FILING_SUMMARY_PROMPT,
)
from ai.prompts.templates import (
    stock_analysis_prompt,
    comparison_prompt,
    earnings_analysis_prompt,
    macro_analysis_prompt,
    sector_analysis_prompt,
    deep_research_prompt,
)


# ── System Prompts ──

class TestBaseSystemPrompt:
    def test_contains_analyst_persona(self):
        assert "personal senior financial analyst" in BASE_SYSTEM_PROMPT

    def test_contains_note_taking_protocol(self):
        assert "save_note" in BASE_SYSTEM_PROMPT

    def test_contains_confidence_scale(self):
        assert "Confidence Rating Scale" in BASE_SYSTEM_PROMPT

    def test_contains_analysis_framework(self):
        assert "Analysis Framework" in BASE_SYSTEM_PROMPT
        assert "Bull Case / Bear Case" in BASE_SYSTEM_PROMPT
        assert "Self-Critique" in BASE_SYSTEM_PROMPT

    def test_contains_portfolio_tracking(self):
        assert "Portfolio tracking" in BASE_SYSTEM_PROMPT

    def test_contains_note_types(self):
        for note_type in ["insight", "decision", "action item", "preference", "concern"]:
            assert note_type in BASE_SYSTEM_PROMPT

    def test_proactive_personality(self):
        assert "Proactive" in BASE_SYSTEM_PROMPT

    def test_memory_driven_personality(self):
        assert "Memory-driven" in BASE_SYSTEM_PROMPT


class TestResearchSystemPrompt:
    def test_extends_base(self):
        assert BASE_SYSTEM_PROMPT in RESEARCH_SYSTEM_PROMPT

    def test_contains_confidence_assessment(self):
        assert "Confidence Assessment" in RESEARCH_SYSTEM_PROMPT

    def test_contains_self_critique_protocol(self):
        assert "Self-Critique Protocol" in RESEARCH_SYSTEM_PROMPT

    def test_contains_biggest_risk(self):
        assert "Biggest Risk" in RESEARCH_SYSTEM_PROMPT

    def test_contains_would_change_view(self):
        assert "Would Change My View If" in RESEARCH_SYSTEM_PROMPT

    def test_contains_data_quality(self):
        assert "Data Quality" in RESEARCH_SYSTEM_PROMPT

    def test_contains_disconfirming_evidence(self):
        assert "disconfirming evidence" in RESEARCH_SYSTEM_PROMPT


class TestBriefingPrompt:
    def test_extends_base(self):
        assert BASE_SYSTEM_PROMPT in BRIEFING_SYSTEM_PROMPT

    def test_contains_market_overview(self):
        assert "Market Overview" in BRIEFING_SYSTEM_PROMPT


class TestClassificationPrompt:
    def test_is_json_format(self):
        assert "JSON" in CLASSIFICATION_SYSTEM_PROMPT

    def test_contains_categories(self):
        assert "earnings" in CLASSIFICATION_SYSTEM_PROMPT
        assert "analyst_action" in CLASSIFICATION_SYSTEM_PROMPT
        assert "macro" in CLASSIFICATION_SYSTEM_PROMPT


# ── Analysis Templates ──

class TestStockAnalysisPrompt:
    def test_contains_symbol(self):
        prompt = stock_analysis_prompt("AAPL")
        assert "AAPL" in prompt

    def test_contains_confidence_assessment(self):
        prompt = stock_analysis_prompt("MSFT")
        assert "Confidence Assessment" in prompt

    def test_contains_self_critique(self):
        prompt = stock_analysis_prompt("TSLA")
        assert "Self-Critique" in prompt

    def test_contains_biggest_risk(self):
        prompt = stock_analysis_prompt("NVDA")
        assert "Biggest Risk" in prompt

    def test_custom_metrics(self):
        prompt = stock_analysis_prompt("AAPL", metrics=["pe_ratio", "roe"])
        assert "pe_ratio" in prompt
        assert "roe" in prompt

    def test_default_metrics(self):
        prompt = stock_analysis_prompt("AAPL")
        assert "PE" in prompt


class TestDeepResearchPrompt:
    def test_contains_symbol(self):
        prompt = deep_research_prompt("NVDA")
        assert "NVDA" in prompt

    def test_contains_confidence_rating(self):
        prompt = deep_research_prompt("AAPL")
        assert "Confidence" in prompt
        assert "1-10" in prompt

    def test_contains_weakest_point(self):
        prompt = deep_research_prompt("AAPL")
        assert "Weakest Point" in prompt

    def test_contains_disconfirming_evidence(self):
        prompt = deep_research_prompt("AAPL")
        assert "Disconfirming Evidence" in prompt

    def test_contains_data_gaps(self):
        prompt = deep_research_prompt("AAPL")
        assert "Data Gaps" in prompt

    def test_contains_would_change_view(self):
        prompt = deep_research_prompt("AAPL")
        assert "Would Change My View If" in prompt


class TestComparisonPrompt:
    def test_contains_all_symbols(self):
        prompt = comparison_prompt(["AAPL", "MSFT", "GOOGL"])
        assert "AAPL" in prompt
        assert "MSFT" in prompt
        assert "GOOGL" in prompt


class TestEarningsPrompt:
    def test_contains_quarter_and_year(self):
        prompt = earnings_analysis_prompt("AAPL", 2024, 4)
        assert "Q4" in prompt
        assert "2024" in prompt
        assert "AAPL" in prompt


class TestMacroPrompt:
    def test_contains_key_indicators(self):
        prompt = macro_analysis_prompt()
        assert "GDP" in prompt
        assert "CPI" in prompt
        assert "VIX" in prompt


class TestSectorPrompt:
    def test_specific_sector(self):
        prompt = sector_analysis_prompt("Technology")
        assert "Technology" in prompt

    def test_all_sectors(self):
        prompt = sector_analysis_prompt()
        assert "sector" in prompt.lower()
