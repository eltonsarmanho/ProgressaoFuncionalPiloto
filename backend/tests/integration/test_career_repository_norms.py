"""NLINK-01, NTIT-06: norm code and required titration of a career version, on PostgreSQL."""

import json
import uuid
from dataclasses import replace
from datetime import date

from sqlalchemy import text

from app.domain.entities.career import CareerClass, CareerVersion
from app.domain.entities.professor import Titration
from tests.integration.test_repositories import (  # noqa: F401  (fixture and helpers)
    _process,
    _professor,
    base,
)

STRUCTURE = "MAGISTERIO_SUPERIOR"


def _version(**kw) -> CareerVersion:
    data = dict(
        name="Estrutura sintética",
        valid_from=date(2025, 1, 1),
        valid_to=None,
        norm_reference="Norma sintética, art. 1º",
        classes=(
            CareerClass("A", ("Inicial",), (1,), None),
            CareerClass("B", ("Intermediária",), (1, 2), 36),
            CareerClass("C", ("Final",), (1,), 24),
        ),
        progression_min_months=24,
    )
    data.update(kw)
    return CareerVersion(**data)


def _titration(version: CareerVersion, code: str) -> Titration | None:
    return version.get_class(code).required_titration


def test_a_row_saved_before_the_new_fields_reads_none_for_all_three(
    engine, uow_factory, base  # noqa: F811
):
    definition = {
        "progression_min_months": 24,
        "classes": [
            {"code": "A", "denominations": ["I"], "levels": [1], "promotion_min_months": None},
            {"code": "B", "denominations": ["F"], "levels": [1], "promotion_min_months": 24},
        ],
    }
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO career_versions (id, structure_id, name, norm_reference, definition) "
                "VALUES (:i, :s, 'Antiga', 'ref', CAST(:d AS jsonb))"
            ),
            {"i": uuid.uuid4(), "s": base["structure_id"], "d": json.dumps(definition)},
        )

    with uow_factory() as uow:
        (version,) = uow.career_versions.list_versions(STRUCTURE)

    assert version.norm_code is None
    assert version.required_titration_norm_code is None
    assert [c.required_titration for c in version.classes] == [None, None]


def test_the_three_fields_make_a_round_trip_through_add_and_list(
    uow_factory, base  # noqa: F811
):
    version = _version(
        norm_code="NORMA-A",
        required_titration_norm_code="NORMA-B",
        classes=(
            CareerClass("A", ("Inicial",), (1,), None),
            CareerClass("B", ("Intermediária",), (1, 2), 36, Titration.MESTRADO),
            CareerClass("C", ("Final",), (1,), 24, Titration.DOUTORADO),
        ),
    )
    with uow_factory() as uow:
        uow.career_versions.add(STRUCTURE, version)
        uow.commit()

    with uow_factory() as uow:
        (stored,) = uow.career_versions.list_versions(STRUCTURE)

    assert stored == version
    assert stored.norm_code == "NORMA-A"
    assert stored.required_titration_norm_code == "NORMA-B"
    assert [c.required_titration for c in stored.classes] == [
        None,
        Titration.MESTRADO,
        Titration.DOUTORADO,
    ]


def test_update_keeps_and_changes_the_three_fields(
    uow_factory, base  # noqa: F811
):
    with uow_factory() as uow:
        uow.career_versions.add(STRUCTURE, _version(norm_code="NORMA-A"))
        uow.commit()
    with uow_factory() as uow:
        (stored,) = uow.career_versions.list_versions(STRUCTURE)
        changed = replace(
            stored,
            norm_code="NORMA-NOVA",
            required_titration_norm_code="NORMA-T",
            classes=(
                stored.classes[0],
                stored.classes[1],
                replace(stored.classes[2], required_titration=Titration.DOUTORADO),
            ),
        )
        uow.career_versions.update(changed)
        uow.commit()

    with uow_factory() as uow:
        (again,) = uow.career_versions.list_versions(STRUCTURE)

    assert again == changed
    assert (again.norm_code, again.required_titration_norm_code) == ("NORMA-NOVA", "NORMA-T")
    assert _titration(again, "C") is Titration.DOUTORADO


def test_set_links_on_a_version_used_by_a_process_writes_the_links_and_nothing_else(
    uow_factory, base  # noqa: F811
):
    professor = _professor(base)
    process = _process(base, professor.id)
    original = _version()
    with uow_factory() as uow:
        uow.career_versions.add(STRUCTURE, original)
        uow.professors.add(professor)
        uow.processes.add(process)
        uow.commit()
    with uow_factory() as uow:
        (stored,) = uow.career_versions.list_versions(STRUCTURE)
        assert uow.processes.get(process.id) is not None  # the version is in use
        uow.career_versions.set_links(
            stored.id,
            norm_code="NORMA-A",
            titrations={"C": Titration.DOUTORADO},
            titration_norm_code="NORMA-T",
        )
        uow.commit()

    with uow_factory() as uow:
        (linked,) = uow.career_versions.list_versions(STRUCTURE)

    assert linked.norm_code == "NORMA-A"
    assert linked.required_titration_norm_code == "NORMA-T"
    assert _titration(linked, "C") is Titration.DOUTORADO
    assert _titration(linked, "A") is None and _titration(linked, "B") is None
    # classes, levels, denominations, months, name and validity stay as they were
    assert replace(
        linked,
        norm_code=None,
        required_titration_norm_code=None,
        classes=tuple(replace(c, required_titration=None) for c in linked.classes),
    ) == original
