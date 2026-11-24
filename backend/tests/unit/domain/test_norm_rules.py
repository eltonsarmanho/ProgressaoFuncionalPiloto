"""NBASE-02, NBASE-03, NBASE-04: field validation of a norm (synthetic values)."""

from datetime import date

import pytest

from app.domain.entities.norm import NormKind
from app.domain.rules.norm_rules import FieldError, validate_norm

VALID = dict(
    code="NORMA-SINTETICA-1",
    title="Norma sintética de teste",
    kind=NormKind.RESOLUCAO,
    issuer="Conselho Sintético",
    published_on=date(2020, 5, 4),
    valid_from=date(2020, 6, 1),
    valid_to=None,
    source_url="https://exemplo.invalid/norma",
    notes=None,
)


def fields_of(errors: list[FieldError]) -> list[str]:
    return [e.field for e in errors]


def test_valid_norm_has_no_errors():
    assert validate_norm(VALID) == []


# NBASE-02: each required field missing errors on that field
@pytest.mark.parametrize("field", ["code", "title", "kind", "issuer", "published_on"])
@pytest.mark.parametrize("empty", [None, ""], ids=["none", "empty"])
def test_missing_required_field_errors_on_that_field(field, empty):
    if field in {"kind", "published_on"} and empty == "":
        empty = None
    errors = validate_norm({**VALID, field: empty})
    assert fields_of(errors) == [field]
    assert errors[0].message.strip()


def test_blank_title_and_issuer_are_missing():
    assert fields_of(validate_norm({**VALID, "title": "   ", "issuer": "  "})) == [
        "title",
        "issuer",
    ]


# NBASE-02: code pattern ^[A-Z0-9][A-Z0-9-]{1,49}$
@pytest.mark.parametrize(
    "code",
    ["norma-sintetica", "NORMA SINTETICA", "A" * 51, "-NORMA", "A"],
    ids=["lowercase", "space", "51-chars", "leading-dash", "1-char"],
)
def test_code_outside_the_pattern_is_refused_on_code(code):
    assert fields_of(validate_norm({**VALID, "code": code})) == ["code"]


@pytest.mark.parametrize("code", ["A" * 50, "LEI-12772-2012", "AB"], ids=["50", "real", "2"])
def test_code_inside_the_pattern_passes(code):
    assert validate_norm({**VALID, "code": code}) == []


# NBASE-03: end of validity not before the start
def test_end_equal_to_start_passes():
    assert validate_norm({**VALID, "valid_to": date(2020, 6, 1)}) == []


def test_end_one_day_before_start_is_refused_on_valid_to():
    assert fields_of(validate_norm({**VALID, "valid_to": date(2020, 5, 31)})) == ["valid_to"]


def test_end_without_start_passes():
    assert validate_norm({**VALID, "valid_from": None, "valid_to": date(2020, 5, 31)}) == []


# NBASE-04: URL starts with https:// or http://
@pytest.mark.parametrize("url", ["ftp://exemplo.invalid/n", "www.exemplo.invalid/n"])
def test_url_without_http_scheme_is_refused_on_source_url(url):
    assert fields_of(validate_norm({**VALID, "source_url": url})) == ["source_url"]


@pytest.mark.parametrize(
    "url", ["http://exemplo.invalid/n", "https://exemplo.invalid/n", None, ""],
    ids=["http", "https", "none", "empty"],
)
def test_http_https_or_empty_url_passes(url):
    assert validate_norm({**VALID, "source_url": url}) == []


# Design: title up to 500, issuer up to 255, notes up to 5 000 characters
@pytest.mark.parametrize(
    ("field", "limit"), [("title", 500), ("issuer", 255), ("notes", 5000)]
)
def test_text_length_limits(field, limit):
    assert validate_norm({**VALID, field: "x" * limit}) == []
    assert fields_of(validate_norm({**VALID, field: "x" * (limit + 1)})) == [field]
