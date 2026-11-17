"""OFI-06, OFI-07: IV.4 hours go through the seeded official table and the scoring endpoint."""

import pytest

from app.domain.entities.user import Role
from app.infrastructure.database.seed import seed_scoring_tables
from tests.integration.api.factories import add_professor, process_payload


@pytest.fixture
def score_course(client, act_as, reference, uow_factory):
    """Scoring of a process on the official table with one IV.4 course of the given hours."""
    seed_scoring_tables(uow_factory())
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    with uow_factory() as uow:
        table = next(
            t for t in uow.scoring_tables.list_tables() if t.name == "Tabela de Pontuação da UFPA"
        )
        version = uow.scoring_tables.list_versions(table.id)[0]
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert process.status_code == 201, process.text
    process_id = process.json()["id"]
    chosen = client.put(
        f"/api/processes/{process_id}/scoring/table",
        json={"version_id": str(version.id)},
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text

    def score(hours):
        body = {
            "title": "Curso de extensão",
            "group_number": 4,
            "item_number": 4,
            "quantidade": 1,
            "event_date": "2023-05-10",
            "evidence_note": "Certificado",
        }
        if hours is not None:
            body["horas"] = hours
        created = client.post(f"/api/processes/{process_id}/activities", json=body, headers=headers)
        assert created.status_code == 201, created.text
        result = client.get(f"/api/processes/{process_id}/scoring").json()
        (row,) = result["rows"]
        return result, row

    return score


def test_nineteen_hours_do_not_score_with_the_insufficient_hours_reason(score_course):
    result, row = score_course(19)

    assert (row["status"], row["reasons"], row["points"]) == (
        "NAO_PONTUADA",
        ["CARGA_HORARIA_INSUFICIENTE"],
        "0.00",
    )
    assert result["total"] == "0.00"


@pytest.mark.parametrize("hours", [20, 21])
def test_twenty_hours_or_more_score_the_two_points_of_iv_4(score_course, hours):
    result, row = score_course(hours)

    assert (row["status"], row["reasons"], row["points"]) == ("PONTUADA", [], "2.00")
    assert "CARGA_HORARIA_NAO_INFORMADA" not in [a["code"] for a in row["alerts"]]
    assert result["total"] == "2.00"


def test_missing_hours_score_with_the_not_informed_alert(score_course):
    result, row = score_course(None)

    assert (row["status"], row["points"]) == ("PONTUADA", "2.00")
    alert = next(a for a in row["alerts"] if a["code"] == "CARGA_HORARIA_NAO_INFORMADA")
    assert alert["severity"] == "ALERTA"
    assert result["total"] == "2.00"
