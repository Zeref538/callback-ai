import pytest

from callback_ai.llm.json_parse import MalformedModelJSON, parse_json_response


def test_clean_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_fenced_json():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_fenced_without_language_tag():
    assert parse_json_response('```\n{"a": 1}\n```') == {"a": 1}


def test_prose_before_and_after():
    raw = 'Sure! Here is the JSON:\n{"a": 1, "b": "x"}\nLet me know if you need changes.'
    assert parse_json_response(raw) == {"a": 1, "b": "x"}


def test_nested_braces():
    raw = 'text {"outer": {"inner": [1, 2]}, "z": 3} tail'
    assert parse_json_response(raw) == {"outer": {"inner": [1, 2]}, "z": 3}


def test_braces_inside_strings_do_not_break_balance():
    raw = 'prefix {"quote": "he said {not json} here", "n": 2} suffix'
    assert parse_json_response(raw) == {"quote": "he said {not json} here", "n": 2}


def test_escaped_quote_inside_string():
    raw = r'{"quote": "she said \"hi\" loudly"}'
    assert parse_json_response(raw) == {"quote": 'she said "hi" loudly'}


def test_no_json_raises():
    with pytest.raises(MalformedModelJSON):
        parse_json_response("I'm sorry, I can't help with that.")


def test_none_raises():
    with pytest.raises(MalformedModelJSON):
        parse_json_response(None)
