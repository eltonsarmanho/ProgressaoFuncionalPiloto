"""NLINK-03, NLINK-05: resolving the norm codes of a set of alerts in one query."""

import logging
import uuid
from datetime import date

from app.application.services.norm_citations import cite_norms
from app.domain.entities.norm import Norm, NormKind


def _norm(code: str, **kw) -> Norm:
    data = dict(
        id=uuid.uuid4(),
        code=code,
        title=f"Norma sintética {code}",
        kind=NormKind.RESOLUCAO,
        issuer="Órgão sintético",
        published_on=date(2020, 3, 4),
    )
    data.update(kw)
    return Norm(**data)


def _store(uow_factory, *norms: Norm) -> None:
    with uow_factory() as uow:
        for norm in norms:
            uow.norms.add(norm)
        uow.commit()


def test_two_registered_codes_become_two_citations(uow_factory):
    a = _norm("NORMA-A", source_url="https://exemplo.invalido/a")
    b = _norm("NORMA-B")
    _store(uow_factory, a, b)

    with uow_factory() as uow:
        cited = cite_norms(uow, ["NORMA-A", "NORMA-B"])

    assert dict(cited) == {"NORMA-A": a.citation(), "NORMA-B": b.citation()}
    assert cited["NORMA-A"].source_url == "https://exemplo.invalido/a"
    assert cited["NORMA-A"].title == "Norma sintética NORMA-A"


def test_none_and_repeated_codes_are_ignored(uow_factory):
    a = _norm("NORMA-A")
    _store(uow_factory, a)

    with uow_factory() as uow:
        cited = cite_norms(uow, [None, "NORMA-A", "NORMA-A", None])

    assert dict(cited) == {"NORMA-A": a.citation()}


def test_a_missing_code_is_left_out_and_logged_with_the_code(uow_factory, caplog):
    a = _norm("NORMA-A")
    _store(uow_factory, a)

    with caplog.at_level(logging.WARNING):
        with uow_factory() as uow:
            cited = cite_norms(uow, ["NORMA-A", "CODIGO-AUSENTE"])

    assert dict(cited) == {"NORMA-A": a.citation()}
    assert "norma não cadastrada: CODIGO-AUSENTE" in caplog.messages
    assert not any("NORMA-A" in m for m in caplog.messages)


def test_an_empty_list_does_not_query_the_database():
    class _Norms:
        def by_codes(self, codes):
            raise AssertionError("the database must not be queried")

    class _Uow:
        norms = _Norms()

    assert dict(cite_norms(_Uow(), [])) == {}
    assert dict(cite_norms(_Uow(), [None, None])) == {}


def test_an_archived_norm_comes_with_archived_true_and_a_file_flag(uow_factory):
    from app.domain.entities.norm import NormFile

    old = _norm(
        "NORMA-VELHA",
        archived=True,
        file=NormFile(f"{uuid.uuid4()}.pdf", "velha.pdf", 10, "b" * 64),
    )
    _store(uow_factory, old)

    with uow_factory() as uow:
        cited = cite_norms(uow, ["NORMA-VELHA"])

    assert cited["NORMA-VELHA"].archived is True
    assert cited["NORMA-VELHA"].has_file is True
