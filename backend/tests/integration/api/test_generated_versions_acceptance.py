"""VER-01, VER-02, VER-03, VER-09 (T91): the Tabela generated twice through the API, an activity
changed in between and after, and version 1 downloaded again.

Version 1 has one validated activity, version 2 has two, and a third activity is added after
version 2; the totals are read from the scoring route at each step.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.api.generated_support import (
    add_activity,
    file_url,
    generate,
    generations_url,
    sha256,
)


def stored(engine, tmp_path, row, extension) -> bytes:
    """The bytes of the file of the version, read from the generated storage on the disk."""
    with engine.connect() as conn:
        process_id, name = conn.execute(
            text(
                "SELECT d.process_id, f.internal_name FROM generated_files f "
                "JOIN generated_documents d ON d.id = f.generated_document_id "
                "WHERE d.id = :id AND f.format = :format"
            ),
            {"id": row["id"], "format": extension.upper()},
        ).one()
    return (tmp_path / "storage" / "generated" / str(process_id) / name).read_bytes()


def snapshot_of(engine, row) -> dict:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT snapshot FROM generated_documents WHERE id = :id"), {"id": row["id"]}
        ).scalar_one()


def total_of(client, scenario) -> str:
    return client.get(f"/api/processes/{scenario.process['id']}/scoring").json()["total"]


@pytest.fixture
def versions(client, scenario):
    """The scenario, version 1 and version 2; `scenario.totals` has the total at each moment."""
    totals = [total_of(client, scenario)]
    first = generate(client, scenario.headers, scenario.process, "TABELA")
    add_activity(client, scenario.headers, scenario.process, title="Segunda orientação")
    totals.append(total_of(client, scenario))
    second = generate(client, scenario.headers, scenario.process, "TABELA")
    add_activity(client, scenario.headers, scenario.process, title="Terceira orientação")
    totals.append(total_of(client, scenario))
    scenario.totals = totals
    return scenario, first, second


def test_the_two_versions_have_their_own_numbers_hashes_and_snapshots(
    client, versions, engine, tmp_path
):
    scenario, first, second = versions

    assert (first["version_number"], second["version_number"]) == (1, 2)
    for extension in ("docx", "pdf"):
        hashes = [
            next(f["sha256"] for f in row["files"] if f["format"] == extension.upper())
            for row in (first, second)
        ]
        assert hashes[0] != hashes[1]
        assert hashes == [
            sha256(stored(engine, tmp_path, row, extension)) for row in (first, second)
        ]
    one, two = snapshot_of(engine, first), snapshot_of(engine, second)
    assert len(set(scenario.totals)) == 3  # every change moved the total
    assert (one["total"], two["total"]) == tuple(scenario.totals[:2])
    assert (len(one["activities"]), len(two["activities"])) == (1, 2)
    assert one != two


def test_version_1_downloaded_after_the_changes_is_the_stored_file_byte_for_byte(
    client, versions, engine, tmp_path
):
    scenario, first, second = versions

    for extension in ("docx", "pdf"):
        download = client.get(file_url(first, extension))

        assert download.status_code == 200
        assert download.content == stored(engine, tmp_path, first, extension)
        assert download.headers["etag"] == f'"{sha256(download.content)}"'
        assert download.content != client.get(file_url(second, extension)).content
    summary = client.get(f"/api/generated-documents/{first['id']}").json()["summary"]
    assert (summary["total"], summary["activity_count"]) == (scenario.totals[0], 1)  # not today's


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE generated_documents SET version_number = 9 WHERE id = :id",
        "UPDATE generated_documents SET snapshot = '{}'::jsonb WHERE id = :id",
        "DELETE FROM generated_documents WHERE id = :id",
        "UPDATE generated_files SET sha256 = repeat('0', 64) WHERE generated_document_id = :id",
        "DELETE FROM generated_files WHERE generated_document_id = :id",
    ],
)
def test_a_direct_update_or_delete_of_a_version_is_refused_by_the_database(
    client, versions, engine, statement
):
    _, first, _ = versions

    with pytest.raises(DBAPIError, match="immutable|cannot be deleted"):
        with engine.begin() as conn:
            conn.execute(text(statement), {"id": first["id"]})

    again = client.get(f"/api/generated-documents/{first['id']}").json()
    assert (again["version_number"], again["files"]) == (1, first["files"])


def test_the_history_shows_the_size_of_every_version_as_stored(client, versions, engine, tmp_path):
    scenario, first, second = versions

    rows = {r["id"]: r for r in client.get(generations_url(scenario.process)).json()}

    assert set(rows) == {first["id"], second["id"]}
    for row in (first, second):
        for file in rows[row["id"]]["files"]:
            content = stored(engine, tmp_path, row, file["format"].lower())
            assert file["size_bytes"] == len(content) > 0
