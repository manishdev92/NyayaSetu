"""Request body + header coalescing for `response_language` (S4)."""

from app.api.v1.generate import _coalesce_response_language
from app.api.v1.generate_schemas import GenerateRequest


def test_coalesce_body_hi_wins() -> None:
    assert _coalesce_response_language("hi", "en,en-US;q=0.9") == "hi"


def test_coalesce_body_en_wins_over_accept_hi() -> None:
    assert _coalesce_response_language("en", "hi-IN,hi;q=0.9") == "en"


def test_coalesce_body_hi_latn_wins() -> None:
    assert _coalesce_response_language("hi_latn", "en-GB,en;q=0.9") == "hi_latn"


def test_coalesce_falls_back_to_accept_hi() -> None:
    assert _coalesce_response_language(None, "hi-IN,hi;q=0.9") == "hi"


def test_coalesce_falls_back_to_en() -> None:
    assert _coalesce_response_language(None, "en-GB,en;q=0.9") == "en"
    assert _coalesce_response_language(None, None) == "en"


def test_schema_response_language_valid() -> None:
    g1 = GenerateRequest.model_validate(
        {
            "user_input": "test issue about police",
            "response_language": "hi",
        }
    )
    assert g1.response_language == "hi"
    g2 = GenerateRequest.model_validate({"user_input": "x", "response_language": "Hindi"})
    assert g2.response_language == "hi"
    g2b = GenerateRequest.model_validate({"user_input": "x", "response_language": "hi-Latn"})
    assert g2b.response_language == "hi_latn"
    g3 = GenerateRequest.model_validate({"user_input": "x"})
    assert g3.response_language is None
