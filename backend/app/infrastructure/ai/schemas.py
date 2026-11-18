"""Strict JSON schemas for the AI extraction, one per document type (EXT-09).

All types share one shape; only the descriptions change. Every property is required, factual
fields accept `null`, and `additionalProperties` is false, so a missing datum is an explicit
`null` and a field the schema does not know is refused. The schema is the provider contract
(`response_format`); the AI output stays untrusted (AD-009) and is still checked against the
page text by the analyzer.
"""

import copy
from typing import Any

from app.domain.entities.activity import Level
from app.domain.entities.extraction import DocumentType, TaxonomyCode

Schema = dict[str, Any]

_TYPE_HINTS: dict[DocumentType, str] = {
    DocumentType.DECLARACAO_BANCA: "Declaração de participação em banca examinadora.",
    DocumentType.DECLARACAO_ORIENTACAO: "Declaração de orientação ou coorientação.",
    DocumentType.DECLARACAO_DISCIPLINAS: (
        "Declaração de componentes curriculares ministrados; uma atividade por oferta."
    ),
    DocumentType.ATA_DEFESA: "Ata de defesa de trabalho acadêmico.",
    DocumentType.CERTIFICADO: "Certificado de curso, evento, treinamento ou participação.",
    DocumentType.PORTARIA: "Portaria de designação para função, comissão ou colegiado.",
    DocumentType.ARTIGO: "Artigo, capítulo ou trabalho publicado; o título e o ISSN ou DOI.",
    DocumentType.REGISTRO_SOFTWARE: "Certificado de registro de programa de computador.",
    DocumentType.OUTRO: "Documento de tipo não identificado.",
}

_ACTIVITY_FIELDS: tuple[tuple[str, Schema], ...] = (
    ("taxonomy", {"type": "string", "enum": [code.value for code in TaxonomyCode]}),
    ("title", {"type": ["string", "null"], "description": "Título ou nome da atividade."}),
    ("role", {"type": ["string", "null"], "description": "Papel do docente, como membro."}),
    ("start_date", {"type": ["string", "null"], "description": "Início, AAAA-MM-DD."}),
    ("end_date", {"type": ["string", "null"], "description": "Fim, AAAA-MM-DD."}),
    (
        "term",
        {
            "type": ["string", "null"],
            "description": "Prazo de duração escrito no texto, copiado literalmente, como "
            "'por 2 (dois) anos' ou '24 meses'; nunca uma data calculada.",
        },
    ),
    ("event_date", {"type": ["string", "null"], "description": "Data do evento, AAAA-MM-DD."}),
    ("hours", {"type": ["number", "null"], "description": "Carga horária do docente em horas."}),
    ("course_hours", {"type": ["number", "null"], "description": "Carga horária total do curso."}),
    ("level", {"type": ["string", "null"], "enum": [*(level.value for level in Level), None]}),
    ("academic_period", {"type": ["string", "null"], "description": "Período letivo, 2025/1."}),
    ("identifier", {"type": ["string", "null"], "description": "Número, ISSN, DOI ou registro."}),
    ("page", {"type": "integer", "description": "Número da página [PÁGINA n] de onde veio."}),
    ("evidence_text", {"type": "string", "description": "Trecho literal da página que comprova."}),
    ("confidence", {"type": "number", "description": "Confiança de 0 a 1."}),
)

ACTIVITY_FIELD_NAMES = tuple(name for name, _ in _ACTIVITY_FIELDS)


def _build_schema(document_type: DocumentType) -> Schema:
    return {
        "type": "object",
        "description": _TYPE_HINTS[document_type],
        "additionalProperties": False,
        "required": ["document_type", "docente_nome", "activities"],
        "properties": {
            "document_type": {"type": "string", "enum": [t.value for t in DocumentType]},
            "docente_nome": {
                "type": ["string", "null"],
                "description": "Nome do docente citado no documento.",
            },
            "activities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(ACTIVITY_FIELD_NAMES),
                    "properties": dict(_ACTIVITY_FIELDS),
                },
            },
        },
    }


_SCHEMAS: dict[DocumentType, Schema] = {t: _build_schema(t) for t in DocumentType}


def schema_for(document_type: DocumentType) -> Schema:
    """A copy of the schema of the document type."""
    return copy.deepcopy(_SCHEMAS[document_type])


def response_format(document_type: DocumentType) -> Schema:
    """The `response_format` envelope of the chat completions request."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"extracao_{document_type.value.lower()}",
            "strict": True,
            "schema": schema_for(document_type),
        },
    }


def _matches_type(value: Any, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    return False


def validate_against_schema(value: Any, schema: Schema, path: str = "$") -> list[str]:
    """Errors of `value` against the schema subset used here; empty when valid.

    Supports `type` (one name or a list), `enum`, `required`, `properties`,
    `additionalProperties: false` and `items`.
    """
    errors: list[str] = []
    types = schema.get("type")
    if types is not None:
        names = [types] if isinstance(types, str) else types
        if not any(_matches_type(value, name) for name in names):
            return [f"{path}: tipo inválido"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: valor fora da lista permitida")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        missing = [key for key in schema.get("required", []) if key not in value]
        errors += [f"{path}.{key}: campo ausente" for key in missing]
        if schema.get("additionalProperties") is False:
            unknown = [key for key in value if key not in properties]
            errors += [f"{path}.{key}: campo desconhecido" for key in unknown]
        for key, sub in properties.items():
            if key in value:
                errors += validate_against_schema(value[key], sub, f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors += validate_against_schema(item, schema["items"], f"{path}[{index}]")
    return errors


def validate_response(document_type: DocumentType, data: Any) -> list[str]:
    """Errors of a parsed AI response against the schema of the document type."""
    return validate_against_schema(data, _SCHEMAS[document_type])
