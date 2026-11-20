"""PROC-12, PROC-13, AUD-01, AUD-03; edge cases: concurrent save (409), archived professor."""

from datetime import timedelta

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.factories import FASI_2022_2024, add_professor, process_payload
from tests.support.process_status import conclude_for_test

EDITABLE = dict(FASI_2022_2024)


@pytest.fixture
def professor(uow_factory, reference):
    return add_professor(uow_factory, reference["FASI"])


@pytest.fixture
def secretaria(act_as, reference):
    return act_as("sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id}))


@pytest.fixture
def process(client, secretaria, professor):
    _, headers = secretaria
    response = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert response.status_code == 201
    return response.json()


def put(client, headers, process_id, version, justificativa=None, **changes):
    body = {**EDITABLE, **changes, "expected_version": version}
    if justificativa is not None:
        body["justificativa"] = justificativa
    return client.put(f"/api/processes/{process_id}", json=body, headers=headers)


def set_status(client, headers, process_id, status, version):
    return client.post(
        f"/api/processes/{process_id}/status",
        json={"status": status, "expected_version": version},
        headers=headers,
    )


def test_rascunho_update_without_justification_is_saved_and_audited(
    client, secretaria, process, uow_factory
):
    actor, headers = secretaria

    response = put(client, headers, process["id"], 1, target_level=2)

    assert response.status_code == 200
    body = response.json()
    assert (body["target_level"], body["version"]) == (2, 2)
    # Promotion to D2 (not the first level of D): alerts are recomputed on save
    assert {a["code"] for a in body["alerts"]} == {"MODALIDADE_INCOMPATIVEL"}
    with uow_factory() as uow:
        event = uow.audit.list_for("process", process["id"])[-1]
    assert event.action is AuditAction.UPDATE
    assert event.user_id == actor.id
    assert event.changes == {"target_level": {"before": 1, "after": 2}}
    assert event.justification is None


@pytest.mark.parametrize("justificativa", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_em_andamento_update_without_justification_returns_422(
    client, secretaria, process, justificativa
):
    _, headers = secretaria
    assert set_status(client, headers, process["id"], "EM_ANDAMENTO", 1).status_code == 200

    response = put(client, headers, process["id"], 2, justificativa, target_level=2)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["justificativa"]
    assert client.get(f"/api/processes/{process['id']}").json()["target_level"] == 1


def test_em_andamento_update_with_justification_records_before_after(
    client, secretaria, process, uow_factory
):
    actor, headers = secretaria
    set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)

    response = put(client, headers, process["id"], 2, "Nível conferido na portaria", target_level=2)

    assert response.status_code == 200
    with uow_factory() as uow:
        event = uow.audit.list_for("process", process["id"])[-1]
    assert event.action is AuditAction.UPDATE
    assert event.user_id == actor.id
    assert event.changes == {"target_level": {"before": 1, "after": 2}}
    assert event.justification == "Nível conferido na portaria"


@pytest.mark.parametrize("final_status", ["CONCLUIDO", "ARQUIVADO"])
def test_read_only_process_rejects_changes_with_409(
    client, secretaria, process, uow_factory, final_status
):
    _, headers = secretaria
    version = 1
    path = ["EM_ANDAMENTO"] if final_status == "CONCLUIDO" else ["ARQUIVADO"]
    for status in path:
        assert set_status(client, headers, process["id"], status, version).status_code == 200
        version += 1
    if final_status == "CONCLUIDO":
        conclude_for_test(uow_factory, process["id"])
        version += 1

    response = put(client, headers, process["id"], version, "Tentativa", target_level=2)

    assert response.status_code == 409
    stored = client.get(f"/api/processes/{process['id']}").json()
    assert (stored["status"], stored["target_level"]) == (final_status, 1)


def test_second_save_with_stale_version_returns_409(client, secretaria, process):
    _, headers = secretaria

    first = put(client, headers, process["id"], 1, notes="Primeira gravação")
    second = put(client, headers, process["id"], 1, notes="Segunda gravação")

    assert first.status_code == 200
    assert second.status_code == 409
    assert client.get(f"/api/processes/{process['id']}").json()["notes"] == "Primeira gravação"


def test_status_follows_rascunho_em_andamento_concluido(client, secretaria, process, uow_factory):
    actor, headers = secretaria

    started = set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)
    conclude_for_test(uow_factory, process["id"])
    finished = client.get(f"/api/processes/{process['id']}")

    assert (started.status_code, started.json()["status"]) == (200, "EM_ANDAMENTO")
    assert (finished.status_code, finished.json()["status"]) == (200, "CONCLUIDO")
    with uow_factory() as uow:
        events = uow.audit.list_for("process", process["id"])
    assert [(e.action, e.changes) for e in events[1:]] == [
        (AuditAction.STATUS, {"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}),
    ]
    assert all(e.user_id == actor.id for e in events)


@pytest.mark.parametrize("who", ["docente", "admin"])
def test_start_without_justification_by_linked_docente_or_admin_is_audited(  # CAINI-08
    client, act_as, process, professor, uow_factory, who
):
    if who == "docente":
        actor, headers = act_as("docente@ufpa.br", Role.DOCENTE, professor_id=professor.id)
    else:
        actor, headers = act_as("admin@ufpa.br", Role.ADMIN)

    response = set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["version"]) == ("EM_ANDAMENTO", 2)
    with uow_factory() as uow:
        last = uow.audit.list_for("process", process["id"])[-1]
    assert last.action == AuditAction.STATUS
    assert last.changes == {"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}
    assert last.justification is None
    assert last.user_id == actor.id


@pytest.mark.parametrize("who", ["other-unit-secretaria", "other-docente"])
def test_start_by_a_user_who_cannot_read_the_process_is_404_and_changes_nothing(  # CAINI-09
    client, act_as, reference, process, uow_factory, who
):
    if who == "other-unit-secretaria":
        _, headers = act_as(
            "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
        )
    else:
        stranger = add_professor(
            uow_factory, reference["FASI"], siape="7654321", name="Outro Docente"
        )
        _, headers = act_as("outro@ufpa.br", Role.DOCENTE, professor_id=stranger.id)

    response = set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)

    assert response.status_code == 404
    _, owner = act_as("admin@ufpa.br", Role.ADMIN)
    unchanged = client.get(f"/api/processes/{process['id']}", headers=owner).json()
    assert (unchanged["status"], unchanged["version"]) == ("RASCUNHO", 1)


@pytest.mark.parametrize(
    ("path", "target"),
    [([], "CONCLUIDO"), (["EM_ANDAMENTO", "CONCLUIDO"], "EM_ANDAMENTO"), ([], "RASCUNHO")],
    ids=["skip-em-andamento", "reopen-concluido", "same-status"],
)
def test_transition_outside_table_returns_409(
    client, secretaria, process, uow_factory, path, target
):
    _, headers = secretaria
    for version, status in enumerate(path, start=1):
        if status == "CONCLUIDO":
            conclude_for_test(uow_factory, process["id"])
        else:
            set_status(client, headers, process["id"], status, version)

    response = set_status(client, headers, process["id"], target, len(path) + 1)

    assert response.status_code == 409


def test_concluido_through_the_status_route_is_409_with_the_conclusion_code(
    client, secretaria, process
):
    _, headers = secretaria
    set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)

    response = set_status(client, headers, process["id"], "CONCLUIDO", 2)

    assert response.status_code == 409
    assert response.json()["code"] == "CONCLUSAO_EXIGE_EXCLUSAO"
    stored = client.get(f"/api/processes/{process['id']}").json()
    assert (stored["status"], stored["version"]) == ("EM_ANDAMENTO", 2)


def test_status_change_with_stale_version_returns_409(client, secretaria, process):
    _, headers = secretaria

    response = set_status(client, headers, process["id"], "EM_ANDAMENTO", 7)

    assert response.status_code == 409
    assert client.get(f"/api/processes/{process['id']}").json()["status"] == "RASCUNHO"


def test_only_admin_or_owner_archive(client, act_as, reference, process, professor):
    _, colleague = act_as(
        "sec2.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id})
    )
    by_colleague = set_status(client, colleague, process["id"], "ARQUIVADO", 1)
    _, owner = act_as("docente@ufpa.br", Role.DOCENTE, professor_id=professor.id)
    by_owner = set_status(client, owner, process["id"], "ARQUIVADO", 1)

    assert by_colleague.status_code == 403
    assert (by_owner.status_code, by_owner.json()["status"]) == (200, "ARQUIVADO")


def test_admin_archives_any_process(client, act_as, process):
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)

    response = set_status(client, headers, process["id"], "ARQUIVADO", 1)

    assert (response.status_code, response.json()["status"]) == (200, "ARQUIVADO")


def test_history_is_chronological_with_before_after_values(client, secretaria, process, clock):
    actor, headers = secretaria
    clock.current += timedelta(minutes=1)
    set_status(client, headers, process["id"], "EM_ANDAMENTO", 1)
    clock.current += timedelta(minutes=1)
    put(client, headers, process["id"], 2, "Corrige nível", target_level=2)

    response = client.get(f"/api/processes/{process['id']}/history")

    assert response.status_code == 200
    events = response.json()
    assert [e["action"] for e in events] == ["CREATE", "STATUS", "UPDATE"]
    times = [e["occurred_at"] for e in events]
    assert times == sorted(times) and len(set(times)) == 3
    assert events[1]["changes"] == {"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}
    assert events[2]["changes"] == {"target_level": {"before": 1, "after": 2}}
    assert events[2]["justification"] == "Corrige nível"
    assert {e["user_id"] for e in events} == {str(actor.id)}


def test_history_and_updates_of_unreadable_process_return_404(client, act_as, reference, process):
    _, headers = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.get(f"/api/processes/{process['id']}/history").status_code == 404
    assert put(client, headers, process["id"], 1, notes="x").status_code == 404
    assert set_status(client, headers, process["id"], "EM_ANDAMENTO", 1).status_code == 404


def test_archived_professor_keeps_processes_readable_but_blocks_new_ones(
    client, act_as, process, professor
):
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    archived = client.post(
        f"/api/professors/{professor.id}/archive", json={"expected_version": 1}, headers=headers
    )
    assert archived.status_code == 200

    existing = client.get(f"/api/processes/{process['id']}")
    new = client.post("/api/processes", json=process_payload(professor), headers=headers)

    assert existing.status_code == 200
    assert new.status_code == 422
    assert [error["field"] for error in new.json()["detail"]] == ["professor_id"]
