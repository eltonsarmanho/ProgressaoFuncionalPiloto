"""GP-DEL-04 and GP-DEL-10 for a process that has generated documents (verification of
gestao-processos, T8): the generated files leave the disk through the real wiring of the
generated storage, and every route of the deleted process answers 404."""

from sqlalchemy import text

from tests.integration.api.generated_support import generate, generations_url


def generated_files(tmp_path):
    root = tmp_path / "storage" / "generated"
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []


def test_the_generated_files_leave_the_disk_and_their_rows_are_gone(
    client, scenario, engine, tmp_path
):
    row = generate(client, scenario.headers, scenario.process, "TABELA")
    on_disk = generated_files(tmp_path)
    assert len(on_disk) == len(row["files"]) > 0

    response = client.delete(f"/api/processes/{scenario.process['id']}", headers=scenario.headers)

    assert response.status_code == 204
    assert generated_files(tmp_path) == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM generated_documents")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM generated_files")).scalar_one() == 0


def test_every_route_of_a_deleted_process_with_generated_documents_answers_404(
    client, scenario
):
    generate(client, scenario.headers, scenario.process, "TABELA")
    process_id = scenario.process["id"]
    deleted = client.delete(f"/api/processes/{process_id}", headers=scenario.headers)
    assert deleted.status_code == 204

    routes = (
        f"/api/processes/{process_id}/scoring",
        f"/api/processes/{process_id}/scoring/table",
        f"/api/processes/{process_id}/report-draft",
        f"/api/processes/{process_id}/comprovante-layout",
        f"/api/processes/{process_id}/conclusion",
        generations_url(scenario.process),
    )
    for route in routes:
        assert client.get(route).status_code == 404, route
