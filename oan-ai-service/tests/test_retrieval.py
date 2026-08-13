from app.services.retrieval import (
    extract_product_codes,
    get_application_search_terms,
    is_product_question,
)


def test_extract_product_codes_finds_simple_code():
    assert extract_product_codes("do you have OAN D 25 in stock") == ["OAN D 25"]


def test_extract_product_codes_finds_multiple_codes():
    codes = extract_product_codes("compare OAN D 25 and OAN SI 110")
    assert codes == ["OAN D 25", "OAN SI 110"]


def test_extract_product_codes_is_case_insensitive():
    assert extract_product_codes("looking for oan d 25") == ["oan d 25"]


def test_extract_product_codes_returns_empty_for_no_match():
    assert extract_product_codes("what is your return policy") == []


def test_get_application_search_terms_matches_known_keyword():
    assert get_application_search_terms("we need something for urea") == ["OAN UA"]


def test_get_application_search_terms_matches_multiple_keywords():
    terms = get_application_search_terms("urea and silica flotation additives")
    assert "OAN UA" in terms
    assert "OAN AMFLOAT" in terms


def test_get_application_search_terms_returns_empty_for_no_match():
    assert get_application_search_terms("what are your business hours") == []


def test_is_product_question_true_for_product_keyword():
    assert is_product_question("what defoamer do you recommend") is True


def test_is_product_question_false_for_unrelated_text():
    assert is_product_question("can I speak to a human") is False