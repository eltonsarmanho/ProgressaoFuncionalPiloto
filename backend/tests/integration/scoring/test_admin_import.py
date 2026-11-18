"""ADM-08, ADM-09: all-or-nothing CSV import as a new version."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring_admin import InvalidCsv
from app.domain.entities.audit import AuditAction
from app.domain.entities.scoring import ScoringMode, TableStatus
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed

HEADER = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite"
REFERENCE = "Res. 6.000/2026"
NEW_START = date(2026, 3, 1)
VALID = "\n".join(
    [
        HEADER,
        "2,7,Orientação nova,por aluno,POR_UNIDADE,12.5,,30",
        "4,4,Curso,a cada 3 horas,POR_BLOCO_DE_HORAS,2,3,",
        "1,1,Aulas,horas,CARGA_SEMANAL,,,",
        "8,70,Outra,ponto,VALOR_INFORMADO,,,5",
    ]
)


def versions(world):
    with world.uow_factory() as uow:
        return list(uow.scoring_tables.list_versions(world.fasi_version.table_id))


def do_import(world, admin_uc, text=VALID, **kw):
    return admin_uc.import_csv.execute(
        kw.pop("actor", world.admin),
        kw.pop("table_id", world.fasi_version.table_id),
        kw.pop("valid_from", NEW_START),
        kw.pop("valid_to", None),
        kw.pop("norm_reference", REFERENCE),
        text,
        **kw,
    )


def test_valid_csv_creates_a_version_with_exactly_the_file_rows(world, admin_uc):
    view = do_import(world, admin_uc)

    created = next(v for v in versions(world) if v.id == view.version.id)
    assert created.valid_from == NEW_START
    assert created.norm_reference == REFERENCE
    assert created.status is TableStatus.PENDENTE_VALIDACAO
    assert [(g.number, len(g.criteria)) for g in created.groups] == [
        (1, 1), (2, 1), (3, 0), (4, 1), (5, 0), (6, 0), (7, 0), (8, 1),
    ]  # fmt: skip
    c = created.get_criterion(2, 7)
    assert (c.description, c.unit_label, c.mode) == (
        "Orientação nova", "por aluno", ScoringMode.POR_UNIDADE
    )  # fmt: skip
    assert (c.unit_points, c.max_points) == (Decimal("12.5"), Decimal("30"))
    block = created.get_criterion(4, 4)
    assert (block.unit_points, block.hours_per_block) == (Decimal("2"), Decimal("3"))
    assert created.get_criterion(8, 70).max_points == Decimal("5")


def test_group_names_limits_and_counts_in_total_come_from_the_latest_version(world, admin_uc):
    do_import(world, admin_uc)

    created = versions(world)[-1]
    for group, base in zip(created.groups, world.fasi_version.groups, strict=True):
        assert (group.name, group.counts_in_total, group.max_points) == (
            base.name, base.counts_in_total, base.max_points
        )  # fmt: skip
    assert created.minimums == world.fasi_version.minimums


def test_ifch_group_one_still_does_not_count_after_an_import(world, admin_uc):
    text = HEADER + "\n2,7,Ok,x,POR_UNIDADE,1,,"
    do_import(world, admin_uc, text=text, table_id=world.ifch_version.table_id)

    with world.uow_factory() as uow:
        created = uow.scoring_tables.list_versions(world.ifch_version.table_id)[-1]
    assert created.get_group(1).counts_in_total is False


def test_weekly_load_row_takes_weeks_and_preparation_from_the_same_item(world, admin_uc):
    do_import(world, admin_uc)

    weekly = versions(world)[-1].get_criterion(1, 1)
    assert weekly.mode is ScoringMode.CARGA_SEMANAL
    assert weekly.weeks_per_semester == 17
    assert weekly.prep_ratio == Decimal("1")


def test_weekly_load_row_without_a_base_item_is_a_line_error(world, admin_uc):
    text = HEADER + "\n2,7,Ok,x,POR_UNIDADE,1,,\n3,1,Semanal,horas,CARGA_SEMANAL,,,"

    with pytest.raises(InvalidCsv) as error:
        do_import(world, admin_uc, text=text)

    assert [(e.line, e.field) for e in error.value.errors] == [(3, "modo")]


def test_closes_the_open_version_and_audits_the_import(world, admin_uc):
    view = do_import(world, admin_uc)

    old = versions(world)[0]
    assert old.id == world.fasi_version.id
    assert old.valid_to == date(2026, 2, 28)
    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("scoring_version", str(view.version.id))
    assert event.action is AuditAction.CREATE
    assert event.justification == REFERENCE
    assert event.changes["imported_criteria"] == {"before": None, "after": 4}


def test_any_invalid_row_lists_every_error_and_creates_nothing(world, admin_uc):
    text = "\n".join(
        [
            HEADER,
            "2,7,Ok,x,POR_UNIDADE,10,,",
            "9,1,Ok,x,POR_UNIDADE,10,,",
            "2,8,Ok,x,INEXISTENTE,10,,",
            "2,9,Ok,x,POR_UNIDADE,abc,,",
        ]
    )

    with pytest.raises(InvalidCsv) as error:
        do_import(world, admin_uc, text=text)

    assert [(e.line, e.field) for e in error.value.errors] == [
        (3, "grupo"),
        (4, "modo"),
        (5, "pontos"),
    ]
    [only] = versions(world)
    assert only.valid_to is None  # the open version was not closed
    assert only.id == world.fasi_version.id


def test_missing_header_column_creates_nothing(world, admin_uc):
    with pytest.raises(InvalidCsv) as error:
        do_import(world, admin_uc, text="grupo,item\n1,1")

    assert {e.field for e in error.value.errors} >= {"descricao", "modo"}
    assert len(versions(world)) == 1


def test_process_of_the_open_version_blocks_the_import_with_409(world, admin_uc):
    world.choose.execute(world.admin, world.process.id, world.fasi_version.id, None, None)

    with pytest.raises(Conflict):
        do_import(world, admin_uc, valid_from=date(2024, 11, 23))

    assert len(versions(world)) == 1


def test_validity_and_reference_errors_are_422(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        do_import(world, admin_uc, norm_reference="")
    assert error.value.field == "norm_reference"
    with pytest.raises(ValidationFailed) as error:
        do_import(world, admin_uc, valid_to=date(2026, 1, 1))
    assert error.value.field == "valid_to"


def test_non_admin_is_403_and_unknown_table_is_404(world, admin_uc):
    with pytest.raises(Forbidden):
        do_import(world, admin_uc, actor=world.secretaria)
    with pytest.raises(NotFound):
        do_import(world, admin_uc, table_id=uuid.uuid4())
    assert len(versions(world)) == 1
