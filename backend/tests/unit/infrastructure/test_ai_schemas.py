"""EXT-09: one strict schema per document type, closed taxonomy, null for absent data."""

import copy
import json

import pytest

from app.domain.entities.extraction import DocumentType, TaxonomyCode
from app.infrastructure.ai.schemas import (
    ACTIVITY_FIELD_NAMES,
    response_format,
    schema_for,
    validate_against_schema,
    validate_response,
)

FACTUAL_FIELDS = (
    "title",
    "role",
    "start_date",
    "end_date",
    "event_date",
    "hours",
    "course_hours",
    "level",
    "academic_period",
    "identifier",
)


def sample_activity(**changes):
    activity = {
        "taxonomy": "BANCA_TCC_GRADUACAO",
        "title": "Estudo Ficticio sobre Dados Abertos",
        "role": "membro",
        "start_date": None,
        "end_date": None,
        "event_date": "2025-03-12",
        "hours": None,
        "course_hours": None,
        "level": "GRADUACAO",
        "academic_period": None,
        "identifier": None,
        "page": 1,
        "evidence_text": "participou como membro da banca examinadora",
        "confidence": 0.9,
    }
    return activity | changes


def sample_response(document_type=DocumentType.DECLARACAO_BANCA, **changes):
    response = {
        "document_type": document_type.value,
        "docente_nome": "Fulana de Tal Exemplo",
        "activities": [sample_activity()],
    }
    return response | changes


@pytest.mark.parametrize("document_type", list(DocumentType))
def test_every_document_type_has_a_strict_schema(document_type):
    schema = schema_for(document_type)
    assert schema["additionalProperties"] is False
    assert sorted(schema["required"]) == ["activities", "docente_nome", "document_type"]
    item = schema["properties"]["activities"]["items"]
    assert item["additionalProperties"] is False
    assert sorted(item["required"]) == sorted(ACTIVITY_FIELD_NAMES)
    assert sorted(item["properties"]) == sorted(ACTIVITY_FIELD_NAMES)


@pytest.mark.parametrize("document_type", list(DocumentType))
def test_every_factual_field_accepts_null(document_type):
    item = schema_for(document_type)["properties"]["activities"]["items"]["properties"]
    for name in FACTUAL_FIELDS:
        assert "null" in item[name]["type"], name
    assert "null" in schema_for(document_type)["properties"]["docente_nome"]["type"]


def test_taxonomy_is_a_closed_enum_of_the_taxonomy_codes():
    item = schema_for(DocumentType.OUTRO)["properties"]["activities"]["items"]["properties"]
    assert item["taxonomy"]["enum"] == [code.value for code in TaxonomyCode]
    assert "OUTRA" in item["taxonomy"]["enum"]
    assert len(item["taxonomy"]["enum"]) == len(set(item["taxonomy"]["enum"]))


def test_each_schema_names_its_document_type():
    descriptions = {schema_for(t)["description"] for t in DocumentType}
    assert len(descriptions) == len(DocumentType)


@pytest.mark.parametrize("document_type", list(DocumentType))
def test_valid_sample_response_passes(document_type):
    assert validate_response(document_type, sample_response(document_type)) == []


def test_response_with_all_factual_fields_null_passes():
    activity = sample_activity(**dict.fromkeys(FACTUAL_FIELDS))
    assert validate_response(DocumentType.OUTRO, sample_response(activities=[activity])) == []


def test_empty_activity_list_passes():
    assert validate_response(DocumentType.OUTRO, sample_response(activities=[])) == []


def test_response_with_an_extra_top_level_field_is_refused():
    errors = validate_response(DocumentType.OUTRO, sample_response() | {"pontos": 10})
    assert errors == ["$.pontos: campo desconhecido"]


def test_activity_with_an_extra_field_is_refused():
    activity = sample_activity(pontuacao=3)
    errors = validate_response(DocumentType.OUTRO, sample_response(activities=[activity]))
    assert errors == ["$.activities[0].pontuacao: campo desconhecido"]


@pytest.mark.parametrize("name", ["taxonomy", "title", "hours", "page", "confidence"])
def test_activity_missing_a_field_is_refused(name):
    activity = sample_activity()
    del activity[name]
    errors = validate_response(DocumentType.OUTRO, sample_response(activities=[activity]))
    assert errors == [f"$.activities[0].{name}: campo ausente"]


def test_taxonomy_outside_the_enum_is_refused():
    activity = sample_activity(taxonomy="INVENTADA")
    errors = validate_response(DocumentType.OUTRO, sample_response(activities=[activity]))
    assert errors == ["$.activities[0].taxonomy: valor fora da lista permitida"]


def test_level_outside_the_enum_is_refused_but_null_is_allowed():
    bad = validate_response(
        DocumentType.OUTRO, sample_response(activities=[sample_activity(level="MEDIO")])
    )
    assert bad == ["$.activities[0].level: valor fora da lista permitida"]
    good = validate_response(
        DocumentType.OUTRO, sample_response(activities=[sample_activity(level=None)])
    )
    assert good == []


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("page", "1"),
        ("page", 1.5),
        ("page", True),
        ("hours", "68"),
        ("confidence", None),
        ("evidence_text", None),
        ("title", 7),
    ],
)
def test_wrong_value_types_are_refused(name, value):
    activity = sample_activity(**{name: value})
    errors = validate_response(DocumentType.OUTRO, sample_response(activities=[activity]))
    assert errors == [f"$.activities[0].{name}: tipo inválido"]


def test_numbers_accept_integers_and_floats():
    activity = sample_activity(hours=68, course_hours=30.5, confidence=1)
    assert validate_response(DocumentType.OUTRO, sample_response(activities=[activity])) == []


@pytest.mark.parametrize("payload", [None, [], "texto", 3])
def test_non_object_response_is_refused(payload):
    assert validate_response(DocumentType.OUTRO, payload) == ["$: tipo inválido"]


def test_activities_must_be_a_list():
    errors = validate_response(DocumentType.OUTRO, sample_response(activities={}))
    assert errors == ["$.activities: tipo inválido"]


def test_unknown_document_type_value_is_refused():
    response = sample_response() | {"document_type": "PIADA"}
    errors = validate_response(DocumentType.OUTRO, response)
    assert errors == ["$.document_type: valor fora da lista permitida"]


def test_response_format_is_the_json_schema_envelope():
    envelope = response_format(DocumentType.ATA_DEFESA)
    assert envelope["type"] == "json_schema"
    assert envelope["json_schema"]["name"] == "extracao_ata_defesa"
    assert envelope["json_schema"]["strict"] is True
    assert envelope["json_schema"]["schema"] == schema_for(DocumentType.ATA_DEFESA)
    json.dumps(envelope)


def test_schema_for_returns_a_copy_that_cannot_alter_the_original():
    schema = schema_for(DocumentType.OUTRO)
    schema["properties"]["activities"]["items"]["required"].clear()
    schema["additionalProperties"] = True
    fresh = schema_for(DocumentType.OUTRO)
    assert fresh["additionalProperties"] is False
    assert len(fresh["properties"]["activities"]["items"]["required"]) == len(ACTIVITY_FIELD_NAMES)


def test_validator_follows_the_schema_it_is_given():
    schema = {
        "type": "object",
        "required": ["a"],
        "additionalProperties": False,
        "properties": {"a": {"type": ["integer", "null"]}},
    }
    assert validate_against_schema({"a": None}, schema) == []
    assert validate_against_schema({"a": "x"}, copy.deepcopy(schema)) == ["$.a: tipo inválido"]
