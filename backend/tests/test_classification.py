from app.orchestrator import classify_query, extract_serial_number


class TestClassification:
    def test_plain_serial(self) -> None:
        assert classify_query("143960") == "serial_number"

    def test_hash_prefix(self) -> None:
        assert classify_query("#91000") == "serial_number"

    def test_word_prefix(self) -> None:
        assert classify_query("serial 45231") == "serial_number"

    def test_natural_language(self) -> None:
        assert (
            classify_query("tell me about the 1905 New Departure shipped to China")
            == "natural_language"
        )

    def test_model_name_only(self) -> None:
        assert classify_query("New Departure") == "natural_language"

    def test_three_digits_not_serial(self) -> None:
        assert classify_query("123") == "natural_language"

    def test_ten_digits_not_serial(self) -> None:
        assert classify_query("1234567890") == "natural_language"

    def test_mixed_query_with_serial(self) -> None:
        assert classify_query("serial 143960 nickel finish") == "serial_number"

    def test_extract_from_word_prefix(self) -> None:
        assert extract_serial_number("serial 143960") == "143960"

    def test_extract_from_bare(self) -> None:
        assert extract_serial_number("143960") == "143960"
