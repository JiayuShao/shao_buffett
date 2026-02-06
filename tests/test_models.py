"""Tests for ai/models.py — model configurations."""

import pytest
from ai.models import ModelConfig, HAIKU, SONNET, OPUS, TIER_ROUTINE, TIER_STANDARD, TIER_DEEP


class TestModelConfig:
    def test_frozen_dataclass(self):
        with pytest.raises(AttributeError):
            HAIKU.model_id = "different-model"

    def test_haiku(self):
        assert "haiku" in HAIKU.model_id
        assert HAIKU.max_tokens > 0
        assert HAIKU.cost_per_1k_input > 0

    def test_sonnet(self):
        assert "sonnet" in SONNET.model_id
        assert SONNET.max_tokens > HAIKU.max_tokens

    def test_opus(self):
        assert "opus" in OPUS.model_id
        assert OPUS.cost_per_1k_input > SONNET.cost_per_1k_input

    def test_cost_ordering(self):
        # Haiku < Sonnet < Opus in cost
        assert HAIKU.cost_per_1k_input < SONNET.cost_per_1k_input < OPUS.cost_per_1k_input
        assert HAIKU.cost_per_1k_output < SONNET.cost_per_1k_output < OPUS.cost_per_1k_output

    def test_tier_aliases(self):
        assert TIER_ROUTINE == HAIKU
        assert TIER_STANDARD == SONNET
        assert TIER_DEEP == OPUS

    def test_display_names(self):
        assert HAIKU.display_name != ""
        assert SONNET.display_name != ""
        assert OPUS.display_name != ""
