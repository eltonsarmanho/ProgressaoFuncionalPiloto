"""Field validation of a norm (NBASE-02, NBASE-03, NBASE-04).

Pure: code uniqueness needs the repository and is checked by the use case.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,49}$")
MAX_TITLE = 500
MAX_ISSUER = 255
MAX_NOTES = 5000


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


def _text(fields: Mapping[str, object], name: str) -> str:
    value = fields.get(name)
    return value.strip() if isinstance(value, str) else ""


def validate_norm(fields: Mapping[str, object]) -> list[FieldError]:
    errors: list[FieldError] = []

    code = _text(fields, "code")
    if not code:
        errors.append(FieldError("code", "Código é obrigatório"))
    elif not CODE_PATTERN.match(code):
        errors.append(
            FieldError(
                "code",
                "Código deve ter de 2 a 50 caracteres: letras maiúsculas, números e hífen",
            )
        )

    title = _text(fields, "title")
    if not title:
        errors.append(FieldError("title", "Título é obrigatório"))
    elif len(title) > MAX_TITLE:
        errors.append(FieldError("title", f"Título deve ter até {MAX_TITLE} caracteres"))

    if fields.get("kind") is None:
        errors.append(FieldError("kind", "Tipo é obrigatório"))

    issuer = _text(fields, "issuer")
    if not issuer:
        errors.append(FieldError("issuer", "Órgão emissor é obrigatório"))
    elif len(issuer) > MAX_ISSUER:
        errors.append(FieldError("issuer", f"Órgão emissor deve ter até {MAX_ISSUER} caracteres"))

    if fields.get("published_on") is None:
        errors.append(FieldError("published_on", "Data de publicação é obrigatória"))

    valid_from, valid_to = fields.get("valid_from"), fields.get("valid_to")
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        errors.append(
            FieldError("valid_to", "Fim da vigência não pode ser anterior ao início")
        )

    url = _text(fields, "source_url")
    if url and not url.startswith(("https://", "http://")):
        errors.append(FieldError("source_url", "URL da fonte deve começar com https:// ou http://"))

    notes = fields.get("notes")
    if isinstance(notes, str) and len(notes) > MAX_NOTES:
        errors.append(FieldError("notes", f"Observação deve ter até {MAX_NOTES} caracteres"))

    return errors
