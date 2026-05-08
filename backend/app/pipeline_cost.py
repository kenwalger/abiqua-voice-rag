from dataclasses import dataclass

# Pricing as of May 2026 — approximate, subject to change
# Sources: platform.openai.com/docs/pricing,
#          anthropic.com/pricing, rime.ai/pricing
PRICING = {
    "embedding_per_token": 0.00000002,  # text-embedding-3-small
    "haiku_input_per_token": 0.00000080,  # claude-haiku-4-5 input
    "haiku_output_per_token": 0.00000400,  # claude-haiku-4-5 output
    "rime_per_char": 0.000016,  # Rime Arcana, per character
}

PRICING_DATE = "2026-05-01"


@dataclass
class CostEstimate:
    embedding_tokens: int
    narration_input_tokens: int
    narration_output_tokens: int
    tts_characters: int
    collections_queried: int
    routing_decision: str
    narration_model: str
    embedding_cost_usd: float
    narration_cost_usd: float
    tts_cost_usd: float
    total_cost_usd: float
    daily_cost_at_10k_usd: float
    pricing_date: str


def calculate_cost(
    embedding_tokens: int,
    narration_input_tokens: int,
    narration_output_tokens: int,
    tts_characters: int,
    collections_queried: int,
    routing_decision: str,
    narration_model: str,
) -> CostEstimate:
    embedding_cost = embedding_tokens * PRICING["embedding_per_token"]
    narration_cost = (
        narration_input_tokens * PRICING["haiku_input_per_token"]
        + narration_output_tokens * PRICING["haiku_output_per_token"]
    )
    tts_cost = tts_characters * PRICING["rime_per_char"]
    total = embedding_cost + narration_cost + tts_cost
    return CostEstimate(
        embedding_tokens=embedding_tokens,
        narration_input_tokens=narration_input_tokens,
        narration_output_tokens=narration_output_tokens,
        tts_characters=tts_characters,
        collections_queried=collections_queried,
        routing_decision=routing_decision,
        narration_model=narration_model,
        embedding_cost_usd=round(embedding_cost, 8),
        narration_cost_usd=round(narration_cost, 8),
        tts_cost_usd=round(tts_cost, 8),
        total_cost_usd=round(total, 8),
        daily_cost_at_10k_usd=round(total * 10000, 4),
        pricing_date=PRICING_DATE,
    )
