"""NBASE-11, NBASE-12: the seed of the seven norms, on real PostgreSQL."""

import uuid
from dataclasses import replace
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.domain.entities.norm import Norm, NormKind
from app.infrastructure.database.seed import seed_reference_data
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher

FONTES = Path(__file__).resolve().parents[3] / "docs" / "referencias" / "normas" / "FONTES.md"
APPROX_NOTE = "data de publicação aproximada pelo ano"

# code -> (title, kind, issuer, published_on, source_url); the URLs are those of FONTES.md.
EXPECTED = {
    "LEI-12772-2012": (
        "Lei nº 12.772/2012 (texto compilado, com as Leis 15.141/2025 e 15.367/2026)",
        NormKind.LEI,
        "Presidência da República",
        date(2012, 1, 1),
        "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12772compilado.htm",
    ),
    "RES-4644-2015-CONSEPE": (
        "Resolução nº 4.644/2015-CONSEPE",
        NormKind.RESOLUCAO,
        "CONSEPE/UFPA",
        date(2015, 1, 1),
        "https://sege.ufpa.br/boletim_interno/downloads/resolucoes/consepe/2015/",
    ),
    "RES-4074-2010-CONSEPE": (
        "Resolução nº 4.074/2010-CONSEPE (Planos Acadêmicos)",
        NormKind.RESOLUCAO,
        "CONSEPE/UFPA",
        date(2010, 1, 1),
        "https://ppga.propesp.ufpa.br/ARQUIVOS/regimento_e_normas/"
        "Resolu%C3%A7%C3%A3o%204074%20Planos%20Academicos.pdf",
    ),
    "IN-01-2026-IFCH": (
        "Instrução Normativa nº 1/2026-IFCH",
        NormKind.INSTRUCAO_NORMATIVA,
        "IFCH/UFPA",
        date(2026, 4, 24),
        "https://ifch.ufpa.br/images/PDF/2026/"
        "IFCH-Instrucao_Normativa_sobre_processos_de_progressao_de_docentes.pdf",
    ),
    "MANUAL-PROGEP-PROGRESSAO": (
        "Manual do Servidor: Progressão, promoção e revisão (Magistério Superior e EBTT)",
        NormKind.MANUAL,
        "PROGEP/UFPA",
        date(2026, 11, 12),
        "https://progep.ufpa.br/progep/index.php?option=com_content&view=article&id=2245",
    ),
    "CORRELACAO-PROGEP-2025": (
        "Tabela de correlação do Magistério Superior (jan/2025)",
        NormKind.TABELA,
        "PROGEP/UFPA",
        date(2025, 1, 1),
        "https://progep.ufpa.br/progep/documentos/tabela-vencimentos/magisterio-superior/"
        "Correlacao-Magisterio-Superior-Jan2025.pdf",
    ),
    "TABELA-OFICIAL-UFPA": (
        "Tabela oficial de pontuação para progressão docente da UFPA",
        NormKind.TABELA,
        "UFPA",
        date(2026, 11, 17),
        None,
    ),
}
# Norms whose publication date FONTES.md gives only by year (or month): 1 January and the note.
APPROXIMATE = {
    "LEI-12772-2012",
    "RES-4644-2015-CONSEPE",
    "RES-4074-2010-CONSEPE",
    "CORRELACAO-PROGEP-2025",
}


def _seed(uow_factory) -> None:
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())


def _norm_events(engine) -> list:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT user_id, action, entity_id FROM audit_logs WHERE entity = 'norm' "
                "ORDER BY id"
            )
        ).all()


def test_an_empty_database_gets_the_seven_norms_without_a_file(uow_factory):
    _seed(uow_factory)

    with uow_factory() as uow:
        norms = {n.code: n for n in uow.norms.list(include_archived=True)}

    assert set(norms) == set(EXPECTED)
    for code, (title, kind, issuer, published_on, url) in EXPECTED.items():
        norm = norms[code]
        assert (norm.title, norm.kind, norm.issuer, norm.published_on, norm.source_url) == (
            title,
            kind,
            issuer,
            published_on,
            url,
        )
        assert norm.file is None
        assert norm.archived is False
        assert norm.version == 1


def test_the_official_table_has_no_url_and_every_other_url_is_listed_in_fontes(uow_factory):
    _seed(uow_factory)
    fontes = FONTES.read_text(encoding="utf-8")

    with uow_factory() as uow:
        norms = {n.code: n for n in uow.norms.list()}

    assert norms["TABELA-OFICIAL-UFPA"].source_url is None
    for code, norm in norms.items():
        if code != "TABELA-OFICIAL-UFPA":
            assert norm.source_url in fontes


def test_an_approximate_publication_date_carries_the_note(uow_factory):
    _seed(uow_factory)

    with uow_factory() as uow:
        norms = {n.code: n for n in uow.norms.list()}

    for code, norm in norms.items():
        has_note = APPROX_NOTE in (norm.notes or "")
        assert has_note is (code in APPROXIMATE), code


def test_each_inserted_norm_is_audited_as_a_system_change(engine, uow_factory):
    _seed(uow_factory)

    events = _norm_events(engine)

    assert len(events) == 7
    assert {e.action for e in events} == {"CREATE"}
    assert {e.user_id for e in events} == {None}


def test_running_again_creates_neither_duplicates_nor_audit(engine, uow_factory):
    _seed(uow_factory)
    first = _norm_events(engine)

    _seed(uow_factory)

    with uow_factory() as uow:
        assert len(uow.norms.list(include_archived=True)) == 7
    assert _norm_events(engine) == first


def test_a_norm_with_the_same_code_is_left_exactly_as_the_admin_edited_it(engine, uow_factory):
    _seed(uow_factory)
    with uow_factory() as uow:
        stored = uow.norms.get_by_code("LEI-12772-2012")
        edited = replace(
            stored, title="Título editado pelo ADMIN", archived=True, source_url=None, notes="n"
        )
        uow.norms.update(edited, expected_version=stored.version)
        uow.commit()
    events_before = _norm_events(engine)

    _seed(uow_factory)

    with uow_factory() as uow:
        again = uow.norms.get_by_code("LEI-12772-2012")
        assert len(uow.norms.list(include_archived=True)) == 7
    assert (again.title, again.archived, again.source_url, again.notes, again.version) == (
        "Título editado pelo ADMIN",
        True,
        None,
        "n",
        2,
    )
    assert _norm_events(engine) == events_before


def test_only_the_missing_codes_are_inserted_and_audited(engine, uow_factory):
    existing = Norm(
        id=uuid.uuid4(),
        code="RES-4644-2015-CONSEPE",
        title="Título que já estava na base",
        kind=NormKind.OUTRO,
        issuer="Outro órgão",
        published_on=date(1999, 9, 9),
    )
    with uow_factory() as uow:
        uow.norms.add(existing)
        uow.commit()

    _seed(uow_factory)

    with uow_factory() as uow:
        norms = {n.code: n for n in uow.norms.list(include_archived=True)}
    assert set(norms) == set(EXPECTED)
    assert norms["RES-4644-2015-CONSEPE"] == existing
    assert len(_norm_events(engine)) == 6
