"""NBASE-01, NBASE-08, NLINK-06: the norm entity and its citation (synthetic norms)."""

import uuid
from datetime import date

from app.domain.entities.norm import Norm, NormCitation, NormFile, NormKind


def synthetic_norm(**changes) -> Norm:
    fields = dict(
        id=uuid.uuid4(),
        code="NORMA-SINTETICA-1",
        title="Norma sintética de teste",
        kind=NormKind.RESOLUCAO,
        issuer="Conselho Sintético",
        published_on=date(2020, 5, 4),
        valid_from=date(2020, 6, 1),
        valid_to=None,
        source_url="https://exemplo.invalid/norma-sintetica",
        file=None,
        notes=None,
        archived=False,
        version=1,
    )
    fields.update(changes)
    return Norm(**fields)


def test_norm_kind_has_the_six_values():
    assert [k.value for k in NormKind] == [
        "LEI",
        "RESOLUCAO",
        "INSTRUCAO_NORMATIVA",
        "MANUAL",
        "TABELA",
        "OUTRO",
    ]


def test_citation_copies_code_title_url_archived_and_id_without_file():
    norm = synthetic_norm()

    assert norm.citation() == NormCitation(
        id=norm.id,
        code="NORMA-SINTETICA-1",
        title="Norma sintética de teste",
        source_url="https://exemplo.invalid/norma-sintetica",
        has_file=False,
        archived=False,
    )


def test_citation_has_file_only_when_the_norm_has_a_file():
    file = NormFile(
        internal_name=f"{uuid.uuid4()}.pdf",
        original_name="norma.pdf",
        size_bytes=1234,
        sha256="0" * 64,
    )
    norm = synthetic_norm(file=file, source_url=None, archived=True)

    citation = norm.citation()

    assert citation.has_file is True
    assert citation.source_url is None
    assert citation.archived is True
