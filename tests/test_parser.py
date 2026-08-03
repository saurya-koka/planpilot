from backend.app.llm import (
    parse_natural_language_request,
)


def test_extracts_chicken_preference(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    parsed = parse_natural_language_request(
        "Plan dinner in Boston for two people. "
        "She only eats chicken."
    )

    assert "chicken options" in parsed.food_preferences
    assert parsed.include_dinner is True


def test_extracts_risotto_preference(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    parsed = parse_natural_language_request(
        "Plan a romantic dinner with risotto "
        "and dessert."
    )

    assert "risotto" in parsed.food_preferences
    assert parsed.include_dinner is True
    assert parsed.include_dessert is True


def test_extracts_public_transit(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    parsed = parse_natural_language_request(
        "Plan a fun outing in Boston. "
        "We have no car."
    )

    assert parsed.transportation == "public_transit"


def test_extracts_budget_and_party_size(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    parsed = parse_natural_language_request(
        "Plan an outing for 4 people under $250."
    )

    assert parsed.party_size == 4
    assert parsed.budget == 250

def test_extracts_written_party_size() -> None:
    result = parse_natural_language_request(
        "Plan a fun outing for five people under $300."
    )

    assert result.party_size == 5
    assert "group" in result.vibes


def test_extracts_multiple_outing_intents() -> None:
    result = parse_natural_language_request(
        "Plan a chill rainy-day outing in Boston."
    )

    assert "chill" in result.vibes
    assert "rainy-day" in result.vibes


def test_group_intent_is_inferred_from_party_size() -> None:
    result = parse_natural_language_request(
        "Plan an outing for 4 people."
    )

    assert result.party_size == 4
    assert "group" in result.vibes
