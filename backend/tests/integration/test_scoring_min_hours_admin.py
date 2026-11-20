"""OFI-06, OFI-12: min_hours is editable through criteria update and travels in the CSV import."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.services.audit_service import AuditService
from app.application.use_cases import scoring_admin
from app.application.use_cases.scoring_admin import EDITABLE_CRITERION_FIELDS
from app.domain.entities.user import Role, User
from app.domain.errors import ValidationFailed
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher

REFERENCE = "Res. 5.000/2026, art. 3"
OFFICIAL = "Tabela de Pontuação da UFPA"
HEADER = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite,min_hours"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


@pytest.fixture
def official(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(uow_factory())
    audit = AuditService(FixedClock())
    with uow_factory() as uow:
        admin = User(uuid.uuid4(), "editor@ufpa.br", "Editor", Role.ADMIN, "x")
        uow.users.add(admin)
        table = next(t for t in uow.scoring_tables.list_tables() if t.name == OFFICIAL)
        version = uow.scoring_tables.list_versions(table.id)[0]
        uow.commit()
    return SimpleNamespace(
        uow_factory=uow_factory,
        admin=admin,
        table_id=table.id,
        version=version,
        update=scoring_admin.UpdateVersionCriteria(uow_factory, audit),
        duplicate=scoring_admin.DuplicateScoringTable(uow_factory, audit),
        import_csv=scoring_admin.ImportCriteriaCsv(uow_factory, audit),
    )


def criterion(world, version_id, group, item):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_version(version_id).get_criterion(group, item)


@pytest.fixture
def unused(official):
    """A copy of the official table: its version is used by no process."""
    view = official.duplicate.execute(official.admin, official.table_id, "Cópia oficial")
    return view.versions[0].version


def test_min_hours_is_an_editable_criterion_field():
    assert "min_hours" in EDITABLE_CRITERION_FIELDS


def test_min_hours_can_be_set_changed_and_cleared_through_criteria_update(official, unused):
    assert criterion(official, unused.id, 4, 6).min_hours is None

    official.update.execute(official.admin, unused.id, 4, 6, {"min_hours": "8"}, REFERENCE)
    assert criterion(official, unused.id, 4, 6).min_hours == Decimal("8")

    official.update.execute(official.admin, unused.id, 4, 3, {"min_hours": "30.5"}, REFERENCE)
    assert criterion(official, unused.id, 4, 3).min_hours == Decimal("30.5")

    official.update.execute(official.admin, unused.id, 4, 3, {"min_hours": None}, REFERENCE)
    assert criterion(official, unused.id, 4, 3).min_hours is None


@pytest.mark.parametrize("value", ["-1", "abc"])
def test_invalid_min_hours_is_422_on_the_field(official, unused, value):
    with pytest.raises(ValidationFailed) as error:
        official.update.execute(official.admin, unused.id, 4, 3, {"min_hours": value}, REFERENCE)

    assert error.value.field == "min_hours"
    assert criterion(official, unused.id, 4, 3).min_hours == Decimal("20")


def test_csv_import_stores_min_hours_and_empty_means_none(official):
    text = "\n".join(
        [
            HEADER,
            "4,3,Curso,por curso,POR_UNIDADE,10,,,20",
            "4,6,Evento,por evento,POR_UNIDADE,5,,,",
        ]
    )

    view = official.import_csv.execute(
        official.admin, official.table_id, date(2026, 12, 1), None, REFERENCE, text
    )

    created = criterion(official, view.version.id, 4, 3)
    assert created.min_hours == Decimal("20")
    assert criterion(official, view.version.id, 4, 6).min_hours is None


def test_csv_import_without_the_min_hours_column_still_works(official):
    text = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite\n"
    text += "4,3,Curso,por curso,POR_UNIDADE,10,,\n"

    view = official.import_csv.execute(
        official.admin, official.table_id, date(2026, 12, 1), None, REFERENCE, text
    )

    assert criterion(official, view.version.id, 4, 3).min_hours is None
