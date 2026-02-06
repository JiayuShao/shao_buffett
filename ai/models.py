"""Model tier configurations for the AI engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    display_name: str
    max_tokens: int
    cost_per_1k_input: float   # USD
    cost_per_1k_output: float  # USD


HAIKU = ModelConfig(
    model_id="claude-haiku-4-5-20251001",
    display_name="Haiku 4.5",
    max_tokens=4096,
    cost_per_1k_input=0.001,
    cost_per_1k_output=0.005,
)

SONNET = ModelConfig(
    model_id="claude-sonnet-4-5-20250929",
    display_name="Sonnet 4.5",
    max_tokens=8192,
    cost_per_1k_input=0.003,
    cost_per_1k_output=0.015,
)

OPUS = ModelConfig(
    model_id="claude-opus-4-6",
    display_name="Opus 4.6",
    max_tokens=8192,
    cost_per_1k_input=0.015,
    cost_per_1k_output=0.075,
)

# Model tiers for routing
TIER_ROUTINE = HAIKU      # News classification, simple lookups
TIER_STANDARD = SONNET    # Most analysis, conversation, summaries
TIER_DEEP = OPUS          # DCF modeling, deep research, complex analysis
