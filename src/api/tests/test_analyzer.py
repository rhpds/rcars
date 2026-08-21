import json
from rcars.services.analyzer import parse_analysis_response


def test_dict():
    assert parse_analysis_response('{"key": "val"}') == {"key": "val"}


def test_list():
    assert parse_analysis_response('[{"a": 1}]') == [{"a": 1}]


def test_fenced_json():
    assert parse_analysis_response('```json\n{"x": 1}\n```') == {"x": 1}


def test_scalar_string_returns_none():
    assert parse_analysis_response('"just a string"') is None


def test_scalar_int_returns_none():
    assert parse_analysis_response("42") is None


def test_scalar_bool_returns_none():
    assert parse_analysis_response("true") is None


def test_empty_returns_none():
    assert parse_analysis_response("") is None
    assert parse_analysis_response(None) is None


def test_unparseable_returns_none():
    assert parse_analysis_response("not json at all") is None
