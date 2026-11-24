"""CLS-01: closed taxonomy matching the design table; extracted activity shape."""

import re
from dataclasses import fields
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.entities.activity import Level
from app.domain.entities.extraction import DocumentType, ExtractedActivity, TaxonomyCode

DESIGN = Path(__file__).resolve().parents[4] / ".specs/features/inteligencia-documental/design.md"

# Shorthand in the first column whose expansion is not "replace the last segments".
_OVERRIDES = {("LIVRO_COM_PARECERISTAS", "SEM"): "LIVRO_SEM_PARECERISTAS"}


def _expand(first: str, other: str) -> str:
    """Expand a design shorthand: the extra name replaces the last segments of the first."""
    if (first, other) in _OVERRIDES:
        return _OVERRIDES[(first, other)]
    base, extra = first.split("_"), other.split("_")
    return "_".join(base[: len(base) - len(extra)] + extra)


def design_table_codes() -> set[str]:
    """Taxonomy codes of the first column of the 'Regras de sugestão' table."""
    lines = DESIGN.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Código da taxonomia"))
    codes: set[str] = set()
    used_overrides = set()
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cell = line.split("|")[1]
        parts = re.findall(r"`([A-Z_]+)`", cell)
        codes.add(parts[0])
        for other in parts[1:]:
            if (parts[0], other) in _OVERRIDES:
                used_overrides.add((parts[0], other))
            codes.add(_expand(parts[0], other))
    assert used_overrides == set(_OVERRIDES), "stale override: the design table changed"
    return codes


def test_taxonomy_has_exactly_the_codes_of_the_design_table():
    expected = design_table_codes()
    actual = {c.value for c in TaxonomyCode}
    assert actual == expected, (sorted(actual - expected), sorted(expected - actual))


def test_taxonomy_member_names_equal_values():
    assert all(member.name == member.value for member in TaxonomyCode)


def test_taxonomy_contains_the_codes_the_spec_names():
    names = {c.value for c in TaxonomyCode}
    assert {
        "CURSO_EXTENSAO_CONCLUIDO",
        "CURSO_CONCLUIDO",
        "PARTICIPACAO_EVENTO",
        "TREINAMENTO_INTERNO",
        "PALESTRA",
        "COORIENTACAO_TCC_GRADUACAO",
        "OUTRA",
        "ORIENTACAO_DOUTORADO",
        "COORIENTACAO_DOUTORADO",
        "BANCA_TCC_GRADUACAO",
        "REGISTRO_SOFTWARE",
    } <= names


def test_document_type_has_the_nine_design_values():
    assert {t.value for t in DocumentType} == {
        "DECLARACAO_BANCA",
        "DECLARACAO_ORIENTACAO",
        "DECLARACAO_DISCIPLINAS",
        "ATA_DEFESA",
        "CERTIFICADO",
        "PORTARIA",
        "ARTIGO",
        "REGISTRO_SOFTWARE",
        "OUTRO",
    }


def test_extracted_activity_keeps_page_excerpt_and_confidence():
    act = ExtractedActivity(
        taxonomy=TaxonomyCode.BANCA_TCC_GRADUACAO,
        page=2,
        evidence_text="Participou como membro da banca examinadora",
        confidence=Decimal("0.90"),
    )
    assert act.page == 2
    assert act.evidence_text == "Participou como membro da banca examinadora"
    assert act.confidence == Decimal("0.90")
    assert act.taxonomy is TaxonomyCode.BANCA_TCC_GRADUACAO


def test_extracted_activity_data_fields_default_to_none():
    act = ExtractedActivity(
        taxonomy=TaxonomyCode.OUTRA, page=1, evidence_text="", confidence=Decimal("0.5")
    )
    optional = {
        "title", "role", "start_date", "end_date", "event_date", "term",
        "hours", "course_hours", "level", "academic_period", "identifier",
    }  # fmt: skip
    assert {f.name for f in fields(act)} == optional | {
        "taxonomy",
        "page",
        "evidence_text",
        "confidence",
    }
    assert all(getattr(act, name) is None for name in optional)


def test_extracted_activity_carries_dates_hours_and_level():
    act = ExtractedActivity(
        taxonomy=TaxonomyCode.DISCIPLINA_MINISTRADA,
        page=1,
        evidence_text="x",
        confidence=Decimal("0.8"),
        start_date=date(2022, 8, 1),
        hours=Decimal("68"),
        level=Level.GRADUACAO,
        academic_period="2022.2",
    )
    assert act.start_date == date(2022, 8, 1)
    assert act.hours == Decimal("68")
    assert act.level is Level.GRADUACAO
    assert act.academic_period == "2022.2"
