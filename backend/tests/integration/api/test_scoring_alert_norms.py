"""NLINK-03, NLINK-06, NMIN-01, NMIN-02: the alerts of the scoring and the reference minimum
carry the cited norm, on the table state and on the calculated result."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import Activity
from app.domain.entities.user import Role
from tests.integration.api.factories import (
    REQUERIMENTO_2024_2026,
    add_professor,
    mark_pending,
    process_payload,
)

OFFICIAL_TABLE = "TABELA-OFICIAL-UFPA"
RES_4644 = "RES-4644-2015-CONSEPE"


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


def make_process(client, admin, professor, case=None):
    payload = process_payload(professor, *([case] if case else []))
    response = client.post("/api/processes", json=payload, headers=admin[1])
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def old_process(client, admin, reference, uow_factory):
    """FASI 2022-2024: the interstice ends under the Res. 4.644 structure (numeric minimum)."""
    return make_process(client, admin, add_professor(uow_factory, reference["FASI"]))


@pytest.fixture
def new_process(client, admin, reference, uow_factory):
    """FASI 2024-2026: the interstice ends under the Lei 15.141 structure (minimum not defined)."""
    professor = add_professor(uow_factory, reference["FASI"], siape="7654321")
    return make_process(client, admin, professor, REQUERIMENTO_2024_2026)


def choose(client, admin, process, version):
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(version.id)},
        headers=admin[1],
    )
    assert response.status_code == 200, response.text
    return response.json()


def score(client, process):
    response = client.get(f"/api/processes/{process['id']}/scoring")
    assert response.status_code == 200, response.text
    return response.json()


def add_activity(uow_factory, process, **kw):
    with uow_factory() as uow:
        creator = uow.users.get_by_email("admin@ufpa.br")
        activity = Activity(
            id=uuid.uuid4(), process_id=uuid.UUID(process["id"]), created_by=creator.id, **kw
        )
        uow.activities.add(activity)
        uow.commit()


def registered(uow_factory, code):
    with uow_factory() as uow:
        return uow.norms.get_by_code(code)


def cited(alert, norm):
    return {
        "norm_code": alert["norm_code"],
        "norm_title": alert["norm_title"],
        "norm_url": alert["norm_url"],
        "norm_file_url": alert["norm_file_url"],
        "norm_archived": alert["norm_archived"],
    } == {
        "norm_code": norm.code,
        "norm_title": norm.title,
        "norm_url": norm.source_url,
        "norm_file_url": None,
        "norm_archived": False,
    }


def alert_of(alerts, code):
    found = [a for a in alerts if a["code"] == code]
    assert len(found) == 1, [a["code"] for a in alerts]
    return found[0]


# NLINK-03, NLINK-06: row alerts and table alerts of the scoring
def test_a_row_alert_and_a_table_alert_of_the_scoring_cite_the_official_table(
    client, admin, new_process, scoring_tables, uow_factory
):
    official = registered(uow_factory, OFFICIAL_TABLE)
    mark_pending(uow_factory, scoring_tables["OFICIAL"])
    choose(client, admin, new_process, scoring_tables["OFICIAL"])
    add_activity(
        uow_factory, new_process, title="Orientação", group_number=2, item_number=7,
        quantity=Decimal("4"), event_date=date(2025, 5, 10),
    )  # fmt: skip

    body = score(client, new_process)

    [row] = body["rows"]
    assert cited(alert_of(row["alerts"], "SEM_COMPROVANTE"), official)
    assert cited(alert_of(body["alerts"], "TABELA_PENDENTE_VALIDACAO"), official)


def test_the_table_state_alerts_cite_the_table_and_the_version_brings_its_code(
    client, admin, new_process, scoring_tables, uow_factory
):
    official = registered(uow_factory, OFFICIAL_TABLE)

    state = choose(client, admin, new_process, scoring_tables["OUTRA"])  # table of another unit

    assert cited(alert_of(state["alerts"], "TABELA_DE_OUTRA_UNIDADE"), official)
    assert state["chosen"]["version"]["norm_code"] == OFFICIAL_TABLE
    read = client.get(f"/api/processes/{new_process['id']}/scoring/table").json()
    assert cited(alert_of(read["alerts"], "TABELA_DE_OUTRA_UNIDADE"), official)
    assert read["suggested"]["version"]["norm_code"] == OFFICIAL_TABLE


def test_no_table_found_cites_the_official_table(client, admin, reference, uow_factory):
    official = registered(uow_factory, OFFICIAL_TABLE)
    professor = add_professor(uow_factory, reference["FASI"], siape="1111111")
    old = {**process_payload(professor), "start_date": "2010-01-01", "end_date": "2012-01-01"}
    created = client.post("/api/processes", json=old, headers=admin[1]).json()

    state = client.get(f"/api/processes/{created['id']}/scoring/table").json()

    assert cited(alert_of(state["alerts"], "TABELA_NAO_ENCONTRADA"), official)


def test_a_version_without_a_code_gives_the_row_alert_with_no_norm(
    client, admin, new_process, scoring_tables, uow_factory
):
    with uow_factory() as uow:
        uow.scoring_tables.update_version(replace(scoring_tables["OFICIAL"], norm_code=None))
        uow.commit()
    choose(client, admin, new_process, scoring_tables["OFICIAL"])
    add_activity(
        uow_factory, new_process, title="Orientação", group_number=2, item_number=7,
        quantity=Decimal("4"), event_date=date(2025, 5, 10),
    )  # fmt: skip

    [row] = score(client, new_process)["rows"]

    alert = alert_of(row["alerts"], "SEM_COMPROVANTE")
    assert alert["norm_reference"]
    assert (alert["norm_code"], alert["norm_title"], alert["norm_url"]) == (None, None, None)
    assert (alert["norm_file_url"], alert["norm_archived"]) == (None, False)


# NMIN-01, NMIN-02
def test_in_the_new_structure_the_minimum_stays_undefined_and_cites_the_resolution(
    client, admin, new_process, scoring_tables, uow_factory
):
    res = registered(uow_factory, RES_4644)
    choose(client, admin, new_process, scoring_tables["OFICIAL"])

    body = score(client, new_process)

    assert body["minimum"]["status"] == "NAO_DEFINIDO"
    assert body["minimum"]["minimum"] is None  # no number
    assert body["minimum"]["norm"] == {
        "code": RES_4644,
        "title": res.title,
        "source_url": res.source_url,
        "file_url": None,
        "archived": False,
    }
    assert cited(alert_of(body["alerts"], "MINIMO_NAO_DEFINIDO"), res)


def test_in_the_old_structure_the_numeric_minimum_comes_as_before(
    client, admin, old_process, scoring_tables, uow_factory
):
    choose(client, admin, old_process, scoring_tables["OFICIAL"])
    add_activity(
        uow_factory, old_process, title="Orientação", group_number=2, item_number=7,
        quantity=Decimal("4"), event_date=date(2023, 5, 10),
    )  # fmt: skip

    body = score(client, old_process)

    minimum = body["minimum"]
    assert (minimum["status"], minimum["minimum"], minimum["total"]) == (
        "NAO_ATINGE",
        "100.00",
        "20.00",
    )
    assert minimum["norm"] is None  # the link is only for the minimum that is not defined
    assert "MINIMO_NAO_DEFINIDO" not in [a["code"] for a in body["alerts"]]
