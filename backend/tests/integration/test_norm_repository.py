"""NBASE-01, NBASE-07, NBASE-10, NLINK-05: the norm repository on real PostgreSQL."""

import uuid
from datetime import date

import pytest

from app.domain.entities.norm import Norm, NormFile, NormKind
from app.domain.errors import StaleVersion


def _norm(code: str = "NORMA-SINTETICA", **kw) -> Norm:
    data = dict(
        id=uuid.uuid4(),
        code=code,
        title="Norma sintética",
        kind=NormKind.RESOLUCAO,
        issuer="Órgão sintético",
        published_on=date(2020, 3, 4),
    )
    data.update(kw)
    return Norm(**data)


def _file() -> NormFile:
    return NormFile(
        internal_name=f"{uuid.uuid4()}.pdf",
        original_name="norma-sintetica.pdf",
        size_bytes=1234,
        sha256="a" * 64,
    )


def test_a_norm_without_a_file_is_stored_and_read_back_with_every_field(uow_factory):
    norm = _norm(
        valid_from=date(2020, 4, 1),
        valid_to=date(2030, 4, 1),
        source_url="https://exemplo.invalido/norma",
        notes="Observação sintética",
    )
    with uow_factory() as uow:
        uow.norms.add(norm)
        uow.commit()

    with uow_factory() as uow:
        assert uow.norms.get(norm.id) == norm
        assert uow.norms.get_by_code("NORMA-SINTETICA") == norm
        assert uow.norms.get(uuid.uuid4()) is None
        assert uow.norms.get_by_code("OUTRO-CODIGO") is None


def test_a_norm_with_a_file_keeps_the_four_file_fields(uow_factory):
    norm = _norm(file=_file())
    with uow_factory() as uow:
        uow.norms.add(norm)
        uow.commit()

    with uow_factory() as uow:
        stored = uow.norms.get(norm.id)

    assert stored is not None
    assert stored.file == norm.file
    assert stored.citation().has_file is True


def test_list_hides_the_archived_norms_unless_asked(uow_factory):
    with uow_factory() as uow:
        uow.norms.add(_norm("B-ATIVA", title="Beta"))
        uow.norms.add(_norm("A-ATIVA", title="Alfa"))
        uow.norms.add(_norm("C-ARQUIVADA", title="Gama", archived=True))
        uow.commit()

    with uow_factory() as uow:
        active = uow.norms.list(include_archived=False)
        everything = uow.norms.list(include_archived=True)

    assert {n.code for n in active} == {"A-ATIVA", "B-ATIVA"}
    assert {n.code for n in everything} == {"A-ATIVA", "B-ATIVA", "C-ARQUIVADA"}


def test_by_codes_returns_the_found_norms_by_code_and_ignores_a_missing_code(uow_factory):
    with uow_factory() as uow:
        uow.norms.add(_norm("PRIMEIRA"))
        uow.norms.add(_norm("SEGUNDA", archived=True))
        uow.commit()

    with uow_factory() as uow:
        found = uow.norms.by_codes(["PRIMEIRA", "SEGUNDA", "AUSENTE"])
        nothing = uow.norms.by_codes([])

    assert set(found) == {"PRIMEIRA", "SEGUNDA"}
    assert found["SEGUNDA"].archived is True
    assert dict(nothing) == {}


def test_update_saves_the_fields_keeps_the_code_and_raises_the_version(uow_factory):
    norm = _norm()
    with uow_factory() as uow:
        uow.norms.add(norm)
        uow.commit()

    with uow_factory() as uow:
        stored = uow.norms.get(norm.id)
        stored.title = "Título novo"
        stored.file = _file()
        stored.archived = True
        uow.norms.update(stored, expected_version=1)
        uow.commit()
        assert stored.version == 2

    with uow_factory() as uow:
        again = uow.norms.get(norm.id)

    assert (again.code, again.title, again.archived, again.version) == (
        "NORMA-SINTETICA",
        "Título novo",
        True,
        2,
    )
    assert again.file == stored.file


def test_update_with_an_old_version_raises_stale_version_and_changes_nothing(uow_factory):
    norm = _norm()
    with uow_factory() as uow:
        uow.norms.add(norm)
        uow.commit()
    with uow_factory() as uow:
        first = uow.norms.get(norm.id)
        first.title = "Primeira edição"
        uow.norms.update(first, expected_version=1)
        uow.commit()

    with uow_factory() as uow:
        second = uow.norms.get(norm.id)
        second.title = "Segunda edição, de versão velha"
        with pytest.raises(StaleVersion):
            uow.norms.update(second, expected_version=1)

    with uow_factory() as uow:
        assert uow.norms.get(norm.id).title == "Primeira edição"
