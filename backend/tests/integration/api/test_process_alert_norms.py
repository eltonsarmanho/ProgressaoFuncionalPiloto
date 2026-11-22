"""NLINK-03..06, NTIT-01, NTIT-08: the alerts of a process carry the cited norm and the check
of the titration of the professor, in every response that builds them."""

from dataclasses import replace

import pytest

from app.domain.entities.professor import Titration
from app.domain.entities.user import Role
from tests.integration.api.documents_support import pdf
from tests.integration.api.factories import add_professor, process_payload

# Promotion B4 -> C1 under the Lei 15.141 structure, with 14 months: the interstice is short
# (INTERSTICIO_INSUFICIENTE, from the structure), C asks for a doctorate (NTIT-01) and the
# empty note leaves DADOS_INCOMPLETOS (Res. 4.644).
PROMOTION_B_C = {
    "modality": "PROMOCAO",
    "current_class": "B",
    "current_denomination": "Adjunto",
    "current_level": 4,
    "target_class": "C",
    "target_denomination": "Associado",
    "target_level": 1,
    "start_date": "2025-02-01",
    "end_date": "2026-04-01",
    "opening_date": "2026-05-01",
    "notes": None,
    "resp_name": "Responsável de Teste",
    "resp_position": "Diretor",
    "resp_appointment": "Portaria 1/2025",
    "resp_admin_unit": "Faculdade de Teste",
}
NORM_KEYS = ("norm_code", "norm_title", "norm_url", "norm_file_url", "norm_archived")
NO_NORM = {
    "norm_code": None,
    "norm_title": None,
    "norm_url": None,
    "norm_file_url": None,
    "norm_archived": False,
}


@pytest.fixture
def admin(act_as, reference):
    return act_as("admin@ufpa.br", Role.ADMIN)


@pytest.fixture
def mestre(reference, uow_factory):
    """A professor of the seeded structure whose registered titration is mestrado."""
    professor = add_professor(uow_factory, reference["FASI"])
    with uow_factory() as uow:
        uow.professors.update(replace(professor, titration=Titration.MESTRADO), 1)
        uow.commit()
        return uow.professors.get(professor.id)


@pytest.fixture
def process(client, admin, mestre):
    response = client.post(
        "/api/processes", json=process_payload(mestre, PROMOTION_B_C), headers=admin[1]
    )
    assert response.status_code == 201, response.text
    return response.json()


def alert_of(body, code):
    found = [a for a in body["alerts"] if a["code"] == code]
    assert len(found) == 1, [a["code"] for a in body["alerts"]]
    return found[0]


def read(client, process):
    response = client.get(f"/api/processes/{process['id']}")
    assert response.status_code == 200, response.text
    return response.json()


def registered(uow_factory, code):
    with uow_factory() as uow:
        return uow.norms.get_by_code(code)


def norm_fields(alert):
    return {k: alert[k] for k in NORM_KEYS}


def unlink_structure_norm(uow_factory, norm_code):
    """Point the Lei 15.141 structure at `norm_code` (None: no norm), keeping the rest."""
    with uow_factory() as uow:
        version = next(
            v
            for v in uow.career_versions.list_versions("MAGISTERIO_SUPERIOR")
            if v.norm_code == "LEI-12772-2012"
        )
        uow.career_versions.set_links(
            version.id, norm_code, {}, version.required_titration_norm_code
        )
        uow.commit()


# NLINK-03, NLINK-06
def test_an_alert_from_the_structure_carries_the_code_title_and_source_of_the_lei(
    client, process, uow_factory
):
    lei = registered(uow_factory, "LEI-12772-2012")

    for body in (process, read(client, process)):  # the creation response and the detail
        alert = alert_of(body, "INTERSTICIO_INSUFICIENTE")
        assert alert["norm_reference"]  # the article text stays
        assert norm_fields(alert) == {
            "norm_code": "LEI-12772-2012",
            "norm_title": lei.title,
            "norm_url": lei.source_url,
            "norm_file_url": None,
            "norm_archived": False,
        }
    assert "12.772" in lei.title
    assert lei.source_url.startswith(("https://", "http://"))


def test_an_alert_of_another_rule_carries_its_own_norm(client, process, uow_factory):
    res = registered(uow_factory, "RES-4644-2015-CONSEPE")

    alert = alert_of(read(client, process), "DADOS_INCOMPLETOS")

    assert norm_fields(alert) == {
        "norm_code": "RES-4644-2015-CONSEPE",
        "norm_title": res.title,
        "norm_url": res.source_url,
        "norm_file_url": None,
        "norm_archived": False,
    }


# NLINK-04
def test_a_norm_with_a_file_gives_the_file_url_and_an_archived_one_says_so(
    client, admin, process, uow_factory
):
    lei = registered(uow_factory, "LEI-12772-2012")
    attached = client.put(
        f"/api/norms/{lei.id}/file",
        files={"file": ("lei.pdf", pdf("lei"), "application/pdf")},
        data={"expected_version": lei.version},
        headers=admin[1],
    )
    assert attached.status_code == 200, attached.text

    alert = alert_of(read(client, process), "INTERSTICIO_INSUFICIENTE")
    assert alert["norm_file_url"] == f"/api/norms/{lei.id}/file"
    assert alert["norm_archived"] is False
    assert client.get(alert["norm_file_url"]).status_code == 200

    archived = client.post(
        f"/api/norms/{lei.id}/archive",
        json={"expected_version": attached.json()["version"]},
        headers=admin[1],
    )
    assert archived.status_code == 200
    again = alert_of(read(client, process), "INTERSTICIO_INSUFICIENTE")
    assert again["norm_archived"] is True
    assert again["norm_code"] == "LEI-12772-2012"
    assert again["norm_file_url"] == f"/api/norms/{lei.id}/file"


# NLINK-05
@pytest.mark.parametrize("linked_code", [None, "CODIGO-NAO-CADASTRADO"])
def test_a_rule_without_a_registered_norm_shows_only_the_reference_text(
    client, process, uow_factory, linked_code
):
    unlink_structure_norm(uow_factory, linked_code)

    alert = alert_of(read(client, process), "INTERSTICIO_INSUFICIENTE")

    assert norm_fields(alert) == NO_NORM
    assert alert["norm_reference"]
    assert alert["message"]


# NTIT-01, NTIT-08
def test_a_mestrado_promoted_to_c_gets_the_titration_alert_with_the_manual_and_it_goes_away(
    client, admin, mestre, process, uow_factory
):
    manual = registered(uow_factory, "MANUAL-PROGEP-PROGRESSAO")

    alert = alert_of(read(client, process), "TITULACAO_INSUFICIENTE")

    assert alert["severity"] == "ALERTA"
    assert alert["message"] == (
        "A classe C (Associado) exige doutorado; a titulação cadastrada do docente é mestrado."
    )
    assert norm_fields(alert) == {
        "norm_code": "MANUAL-PROGEP-PROGRESSAO",
        "norm_title": manual.title,
        "norm_url": manual.source_url,
        "norm_file_url": None,
        "norm_archived": False,
    }

    corrected = client.put(
        f"/api/professors/{mestre.id}",
        json={
            "full_name": mestre.full_name,
            "siape": mestre.siape,
            "titration": "DOUTORADO",
            "position": mestre.position,
            "unit_id": str(mestre.unit_id),
            "faculty": mestre.faculty,
            "campus": mestre.campus,
            "work_regime": mestre.work_regime.value,
            "expected_version": mestre.version,
        },
        headers=admin[1],
    )
    assert corrected.status_code == 200, corrected.text
    after = read(client, process)
    assert "TITULACAO_INSUFICIENTE" not in [a["code"] for a in after["alerts"]]
    # the other alerts of the process stay
    assert alert_of(after, "INTERSTICIO_INSUFICIENTE")["norm_code"] == "LEI-12772-2012"


# NTIT-07: the titration alert never blocks editing nor starting the process
def test_the_titration_alert_does_not_block_editing_or_starting_the_process(client, admin, process):
    headers = admin[1]
    assert "TITULACAO_INSUFICIENTE" in [a["code"] for a in process["alerts"]]

    edited = client.put(
        f"/api/processes/{process['id']}",
        json={**PROMOTION_B_C, "notes": "Observação sintética", "expected_version": 1},
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["notes"] == "Observação sintética"
    assert alert_of(edited.json(), "TITULACAO_INSUFICIENTE")["severity"] == "ALERTA"

    started = client.post(
        f"/api/processes/{process['id']}/status",
        json={"status": "EM_ANDAMENTO", "expected_version": edited.json()["version"]},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    stored = read(client, process)
    assert stored["status"] == "EM_ANDAMENTO"
    assert alert_of(stored, "TITULACAO_INSUFICIENTE")["severity"] == "ALERTA"

    edited_again = client.put(
        f"/api/processes/{process['id']}",
        json={
            **PROMOTION_B_C,
            "notes": "Observação sintética 2",
            "expected_version": stored["version"],
            "justificativa": "Ajuste sintético da observação",
        },
        headers=headers,
    )
    assert edited_again.status_code == 200, edited_again.text
    assert alert_of(edited_again.json(), "TITULACAO_INSUFICIENTE")["severity"] == "ALERTA"
