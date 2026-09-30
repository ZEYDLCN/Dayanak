import pytest

from app.llm import parse_generation


def test_valid_abstention_without_answer_fields_is_not_an_error():
    g = parse_generation({"answerable": False}, 2)
    assert g.answerable is False and g.answer == "" and g.used == []


def test_null_fields_on_abstention_are_tolerated():
    g = parse_generation({"answerable": False, "answer": None, "used_passages": None}, 2)
    assert not g.answerable


def test_answerable_requires_text():
    with pytest.raises(ValueError):
        parse_generation({"answerable": True, "answer": "  ", "used_passages": [1]}, 2)


@pytest.mark.parametrize("bad", [None, [], {"answer": "x"}, {"answerable": "true"}, {"answerable": 1}])
def test_answerable_must_be_bool(bad):
    with pytest.raises(ValueError):
        parse_generation(bad, 2)


def test_used_passages_are_one_based_bounded_and_typed():
    assert parse_generation({"answerable": True, "answer": "x", "used_passages": [1, 5, 0]}, 2).used == [0]
    with pytest.raises(ValueError):
        parse_generation({"answerable": True, "answer": "x", "used_passages": ["1"]}, 2)
    with pytest.raises(ValueError):
        parse_generation({"answerable": True, "answer": "x", "used_passages": [True]}, 2)
