from app.pipeline_cost import PRICING, calculate_cost


class TestCostCalculation:
    def test_zero_inputs_produce_zero_costs(self) -> None:
        result = calculate_cost(
            embedding_tokens=0,
            narration_input_tokens=0,
            narration_output_tokens=0,
            tts_characters=0,
            collections_queried=1,
            routing_decision="serial_number",
            narration_model="claude-haiku-4-5-20251001",
        )
        assert result.embedding_cost_usd == 0.0
        assert result.narration_cost_usd == 0.0
        assert result.tts_cost_usd == 0.0
        assert result.total_cost_usd == 0.0
        assert result.daily_cost_at_10k_usd == 0.0

    def test_embedding_cost_matches_constant(self) -> None:
        tokens = 100
        result = calculate_cost(
            embedding_tokens=tokens,
            narration_input_tokens=0,
            narration_output_tokens=0,
            tts_characters=0,
            collections_queried=1,
            routing_decision="serial_number",
            narration_model="claude-haiku-4-5-20251001",
        )
        expected = round(tokens * PRICING["embedding_per_token"], 8)
        assert result.embedding_cost_usd == expected

    def test_narration_cost_matches_constants(self) -> None:
        result = calculate_cost(
            embedding_tokens=0,
            narration_input_tokens=300,
            narration_output_tokens=90,
            tts_characters=0,
            collections_queried=1,
            routing_decision="serial_number",
            narration_model="claude-haiku-4-5-20251001",
        )
        expected = round(
            300 * PRICING["haiku_input_per_token"]
            + 90 * PRICING["haiku_output_per_token"],
            8,
        )
        assert result.narration_cost_usd == expected

    def test_tts_cost_matches_constant(self) -> None:
        chars = 387
        result = calculate_cost(
            embedding_tokens=0,
            narration_input_tokens=0,
            narration_output_tokens=0,
            tts_characters=chars,
            collections_queried=1,
            routing_decision="serial_number",
            narration_model="claude-haiku-4-5-20251001",
        )
        expected = round(chars * PRICING["rime_per_char"], 8)
        assert result.tts_cost_usd == expected

    def test_total_equals_sum_of_parts(self) -> None:
        result = calculate_cost(
            embedding_tokens=50,
            narration_input_tokens=300,
            narration_output_tokens=90,
            tts_characters=387,
            collections_queried=1,
            routing_decision="natural_language",
            narration_model="claude-haiku-4-5-20251001",
        )
        expected_total = round(
            result.embedding_cost_usd
            + result.narration_cost_usd
            + result.tts_cost_usd,
            8,
        )
        assert abs(result.total_cost_usd - expected_total) < 1e-9

    def test_daily_extrapolation(self) -> None:
        result = calculate_cost(
            embedding_tokens=50,
            narration_input_tokens=300,
            narration_output_tokens=90,
            tts_characters=387,
            collections_queried=3,
            routing_decision="natural_language",
            narration_model="claude-haiku-4-5-20251001",
        )
        expected_daily = round(result.total_cost_usd * 10000, 4)
        assert abs(result.daily_cost_at_10k_usd - expected_daily) < 1e-6

    def test_metadata_fields_preserved(self) -> None:
        result = calculate_cost(
            embedding_tokens=8,
            narration_input_tokens=312,
            narration_output_tokens=89,
            tts_characters=387,
            collections_queried=1,
            routing_decision="serial_number",
            narration_model="claude-haiku-4-5-20251001",
        )
        assert result.routing_decision == "serial_number"
        assert result.narration_model == "claude-haiku-4-5-20251001"
        assert result.collections_queried == 1
        assert result.pricing_date == "2026-05-01"
