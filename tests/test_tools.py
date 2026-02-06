"""Tests for ai/tools.py — tool definition integrity."""

import pytest
from ai.tools import FINANCIAL_TOOLS


class TestToolDefinitions:
    """Verify all tool definitions are well-formed."""

    def test_tool_count(self):
        """Should have 20 tools total (12 financial + polymarket + 3 notes + 4 portfolio)."""
        assert len(FINANCIAL_TOOLS) == 20

    def test_all_tools_have_required_fields(self):
        for tool in FINANCIAL_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"
            schema = tool["input_schema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type must be 'object'"
            assert "properties" in schema, f"Tool {tool['name']} missing 'properties'"
            assert "required" in schema, f"Tool {tool['name']} missing 'required'"

    def test_tool_names_are_unique(self):
        names = [t["name"] for t in FINANCIAL_TOOLS]
        assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"

    def test_required_fields_exist_in_properties(self):
        """Every required field must be defined in properties."""
        for tool in FINANCIAL_TOOLS:
            props = set(tool["input_schema"]["properties"].keys())
            required = set(tool["input_schema"]["required"])
            missing = required - props
            assert not missing, f"Tool {tool['name']}: required fields {missing} not in properties"


class TestFinancialToolNames:
    """Verify expected tools exist."""

    def _tool_names(self):
        return {t["name"] for t in FINANCIAL_TOOLS}

    def test_core_financial_tools(self):
        names = self._tool_names()
        expected = {
            "get_quote", "get_company_profile", "get_fundamentals",
            "get_analyst_data", "get_earnings", "get_news",
            "get_macro_data", "get_sector_performance",
            "get_earnings_transcript", "get_sec_filings",
            "get_research_papers", "generate_chart",
        }
        assert expected.issubset(names)

    def test_polymarket_tool(self):
        names = self._tool_names()
        assert "get_polymarket" in names

    def test_note_tools(self):
        names = self._tool_names()
        assert {"save_note", "get_user_notes", "resolve_action_item"}.issubset(names)

    def test_portfolio_tools(self):
        names = self._tool_names()
        assert {"get_portfolio", "update_portfolio", "get_financial_profile", "update_financial_profile"}.issubset(names)


class TestSaveNoteTool:
    def _get_tool(self, name):
        return next(t for t in FINANCIAL_TOOLS if t["name"] == name)

    def test_save_note_requires_type_and_content(self):
        tool = self._get_tool("save_note")
        assert "note_type" in tool["input_schema"]["required"]
        assert "content" in tool["input_schema"]["required"]

    def test_save_note_type_enum(self):
        tool = self._get_tool("save_note")
        enum = tool["input_schema"]["properties"]["note_type"]["enum"]
        assert set(enum) == {"insight", "decision", "action_item", "preference", "concern"}

    def test_save_note_has_symbols_field(self):
        tool = self._get_tool("save_note")
        assert "symbols" in tool["input_schema"]["properties"]


class TestUpdatePortfolioTool:
    def _get_tool(self, name):
        return next(t for t in FINANCIAL_TOOLS if t["name"] == name)

    def test_requires_action_and_symbol(self):
        tool = self._get_tool("update_portfolio")
        assert "action" in tool["input_schema"]["required"]
        assert "symbol" in tool["input_schema"]["required"]

    def test_action_enum(self):
        tool = self._get_tool("update_portfolio")
        assert tool["input_schema"]["properties"]["action"]["enum"] == ["add", "remove"]

    def test_has_cost_basis_field(self):
        tool = self._get_tool("update_portfolio")
        assert "cost_basis" in tool["input_schema"]["properties"]

    def test_has_account_type_field(self):
        tool = self._get_tool("update_portfolio")
        assert "account_type" in tool["input_schema"]["properties"]


class TestPolymarketTool:
    def _get_tool(self, name):
        return next(t for t in FINANCIAL_TOOLS if t["name"] == name)

    def test_requires_query(self):
        tool = self._get_tool("get_polymarket")
        assert "query" in tool["input_schema"]["required"]

    def test_has_limit(self):
        tool = self._get_tool("get_polymarket")
        assert "limit" in tool["input_schema"]["properties"]
