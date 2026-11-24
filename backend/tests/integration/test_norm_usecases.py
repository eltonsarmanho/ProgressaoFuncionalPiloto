"""NBASE-01..10, NLIST-01, NLIST-02: the norm use cases on real PostgreSQL, with synthetic
norms and PDFs generated here."""

import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from app.application.services.audit_service import AuditService
from app.application.services.norm_citations import cite_norms
from app.application.use_cases import norms as norm_cases
from app.application.use_cases.documents import UploadRejected
from app.application.use_cases.norms import NormFields
from app.domain.entities.norm import NormKind
from app.domain.entities.user import Role, User
from app.domain.errors import Forbidden, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import StagedNormFile
from app.domain.rules.career_catalog import LEI_15141_2025, RES_4644_2015
from app.infrastructure.database.seed import (
    STRUCTURE_CODE,
    seed_reference_data,
    seed_scoring_tables,
)
from app.infrastructure.files.inspector import PillowFileInspector
from app.infrastructure.storage.norm_storage import LocalNormStorage
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher

MB = 1024 * 1024


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _user(role: Role) -> User:
    return User(uuid.uuid4(), f"{role.value.lower()}@ufpa.invalido", role.value, role, "x")


def _fields(**kw) -> NormFields:
    data = dict(
        title="Resolução sintética de teste",
        kind=NormKind.RESOLUCAO,
        issuer="Órgão sintético",
        published_on=date(2020, 3, 4),
    )
    data.update(kw)
    return NormFields(**data)


def _pdf(path: Path, text: str = "norma sintetica") -> Path:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    doc.save(path)
    return path


@pytest.fixture
def world(uow_factory, tmp_path):
    audit = AuditService(FixedClock())
    storage = LocalNormStorage(tmp_path / "storage")
    inspector = PillowFileInspector()
    users = {role: _user(role) for role in Role}
    with uow_factory() as uow:
        for user in users.values():
            uow.users.add(user)
        uow.commit()
    codes = (STRUCTURE_CODE,)
    return SimpleNamespace(
        uow_factory=uow_factory,
        tmp=tmp_path,
        storage=storage,
        storage_dir=tmp_path / "storage" / "norms",
        admin=users[Role.ADMIN],
        docente=users[Role.DOCENTE],
        secretaria=users[Role.SECRETARIA],
        create=norm_cases.CreateNorm(uow_factory, audit),
        update=norm_cases.UpdateNorm(uow_factory, audit),
        archive=norm_cases.ArchiveNorm(uow_factory, audit),
        attach=norm_cases.AttachNormFile(uow_factory, audit, storage, inspector),
        attach_with=lambda st: norm_cases.AttachNormFile(uow_factory, audit, st, inspector),
        download=norm_cases.DownloadNormFile(uow_factory, storage),
        list=norm_cases.ListNorms(uow_factory, codes),
        get=norm_cases.GetNorm(uow_factory, codes),
        audit_rows=lambda norm_id: _audit_rows(uow_factory, norm_id),
    )


def _audit_rows(uow_factory, norm_id):
    with uow_factory() as uow:
        return list(uow.audit.list_for("norm", str(norm_id)))


def _staged(world, name="norma.pdf", text="norma sintetica") -> StagedNormFile:
    return StagedNormFile(_pdf(world.tmp / f"{uuid.uuid4().hex}.pdf", text), name)


def _stored_files(world) -> list[str]:
    return sorted(p.name for p in world.storage_dir.glob("*")) if world.storage_dir.exists() else []


def _read(world, norm_id):
    with world.uow_factory() as uow:
        return uow.norms.get(norm_id)


# NBASE-01
def test_creating_a_norm_stores_it_active_and_audits_the_creation(world):
    norm = world.create.execute(
        world.admin, "RES-SINTETICA-2020", _fields(source_url="https://exemplo.invalido/n")
    )

    stored = _read(world, norm.id)
    assert stored.code == "RES-SINTETICA-2020"
    assert stored.archived is False
    assert stored.version == 1
    assert stored.kind is NormKind.RESOLUCAO
    assert stored.source_url == "https://exemplo.invalido/n"
    assert stored.file is None
    (event,) = world.audit_rows(norm.id)
    assert event.action.value == "CREATE"
    assert event.user_id == world.admin.id
    assert event.changes["code"]["after"] == "RES-SINTETICA-2020"
    assert event.changes["title"]["after"] == "Resolução sintética de teste"


# NBASE-02
def test_a_repeated_code_is_422_on_the_code(world):
    world.create.execute(world.admin, "RES-SINTETICA-2020", _fields())

    with pytest.raises(ValidationFailed) as error:
        world.create.execute(world.admin, "RES-SINTETICA-2020", _fields(title="Outra"))

    assert error.value.field == "code"


@pytest.mark.parametrize(
    ("code", "changes", "field"),
    [
        ("", {}, "code"),
        ("RES-X-1", {"title": ""}, "title"),
        ("RES-X-1", {"kind": None}, "kind"),
        ("RES-X-1", {"issuer": ""}, "issuer"),
        ("RES-X-1", {"published_on": None}, "published_on"),
    ],
)
def test_each_missing_required_field_is_422_on_that_field(world, code, changes, field):
    with pytest.raises(ValidationFailed) as error:
        world.create.execute(world.admin, code, _fields(**changes))

    assert error.value.field == field
    with world.uow_factory() as uow:
        assert uow.norms.list(include_archived=True) == []


# NBASE-03
def test_a_validity_end_before_the_start_is_422_on_the_end(world):
    with pytest.raises(ValidationFailed) as error:
        world.create.execute(
            world.admin,
            "RES-X-1",
            _fields(valid_from=date(2021, 1, 10), valid_to=date(2021, 1, 9)),
        )

    assert error.value.field == "valid_to"


# NBASE-04
def test_a_source_url_without_http_is_422_on_the_url(world):
    with pytest.raises(ValidationFailed) as error:
        world.create.execute(world.admin, "RES-X-1", _fields(source_url="www.exemplo.invalido"))

    assert error.value.field == "source_url"


# NBASE-05
def test_attaching_a_pdf_stores_it_and_audits_and_a_second_one_replaces_the_first(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())

    first = world.attach.execute(world.admin, norm.id, _staged(world, "primeira.pdf", "um"), 1)

    assert first.file.original_name == "primeira.pdf"
    assert first.version == 2
    assert _stored_files(world) == [first.file.internal_name]
    assert world.storage.open(first.file.internal_name).read_bytes()[:5] == b"%PDF-"
    assert _read(world, norm.id).file == first.file
    after_first = world.audit_rows(norm.id)[-1]
    assert after_first.action.value == "UPDATE"
    assert after_first.user_id == world.admin.id
    assert after_first.changes["file_original_name"] == {"before": None, "after": "primeira.pdf"}

    second = world.attach.execute(world.admin, norm.id, _staged(world, "segunda.pdf", "dois"), 2)

    assert second.file.internal_name != first.file.internal_name
    assert _stored_files(world) == [second.file.internal_name]  # the first one left the disk
    assert _read(world, norm.id).file == second.file
    after_second = world.audit_rows(norm.id)[-1]
    assert after_second.changes["file_original_name"] == {
        "before": "primeira.pdf",
        "after": "segunda.pdf",
    }


# NBASE-06
@pytest.mark.parametrize("name", ["nota.txt", "imagem.png"])
def test_a_file_that_is_not_a_pdf_is_422(world, name):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    path = world.tmp / "nao-pdf"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100 if name.endswith(".png") else b"texto")

    with pytest.raises(UploadRejected) as error:
        world.attach.execute(world.admin, norm.id, StagedNormFile(path, name), 1)

    assert isinstance(error.value, ValidationFailed)
    assert error.value.field == "arquivo"
    assert _read(world, norm.id).file is None
    assert _stored_files(world) == []


def test_a_pdf_named_png_or_with_a_png_inside_is_422(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    path = world.tmp / "disfarce.pdf"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    with pytest.raises(UploadRejected):
        world.attach.execute(world.admin, norm.id, StagedNormFile(path, "disfarce.pdf"), 1)

    assert _read(world, norm.id).file is None


def test_a_pdf_one_byte_over_20_mb_is_422_with_the_limit_in_the_message(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    path = world.tmp / "grande.pdf"
    path.write_bytes(b"%PDF-1.4\n" + b"0" * (20 * MB + 1 - len(b"%PDF-1.4\n")))
    assert path.stat().st_size == 20 * MB + 1

    with pytest.raises(UploadRejected) as error:
        world.attach.execute(world.admin, norm.id, StagedNormFile(path, "grande.pdf"), 1)

    assert error.value.field == "arquivo"
    assert "20 MB" in error.value.message
    assert _read(world, norm.id).file is None
    assert _stored_files(world) == []


# NBASE-07
def test_editing_a_norm_keeps_the_code_and_audits_the_previous_values(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields(title="Título antigo"))

    edited = world.update.execute(
        world.admin, norm.id, _fields(title="Título novo", notes="Observação"), 1
    )

    assert edited.code == "RES-X-1"
    assert edited.title == "Título novo"
    assert edited.version == 2
    stored = _read(world, norm.id)
    assert (stored.code, stored.title, stored.notes) == ("RES-X-1", "Título novo", "Observação")
    event = world.audit_rows(norm.id)[-1]
    assert event.action.value == "UPDATE"
    assert event.changes["title"] == {"before": "Título antigo", "after": "Título novo"}
    assert event.changes["notes"] == {"before": None, "after": "Observação"}
    assert "code" not in event.changes


# NBASE-08
def test_archiving_marks_the_norm_and_keeps_every_link_to_the_rules(world):
    seed_reference_data(world.uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(world.uow_factory())
    with world.uow_factory() as uow:
        official = uow.norms.get_by_code("TABELA-OFICIAL-UFPA")
    before = world.get.execute(world.admin, official.id)
    assert before.rules

    archived = world.archive.execute(world.admin, official.id, official.version)

    assert archived.archived is True
    after = world.get.execute(world.admin, official.id)
    assert after.norm.archived is True
    assert after.rules == before.rules
    with world.uow_factory() as uow:
        assert cite_norms(uow, ["TABELA-OFICIAL-UFPA"])["TABELA-OFICIAL-UFPA"].archived is True
        tables = uow.scoring_tables.list_tables()
        assert {
            v.norm_code for t in tables for v in uow.scoring_tables.list_versions(t.id)
        } >= {"TABELA-OFICIAL-UFPA"}
    (event,) = [e for e in world.audit_rows(official.id) if e.user_id == world.admin.id]
    assert event.action.value == "ARCHIVE"
    assert event.changes["archived"] == {"before": False, "after": True}


# NBASE-09
def test_only_the_admin_writes_and_everybody_else_gets_forbidden(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            world.create.execute(actor, "RES-X-2", _fields())
        with pytest.raises(Forbidden):
            world.update.execute(actor, norm.id, _fields(title="Outro"), 1)
        with pytest.raises(Forbidden):
            world.archive.execute(actor, norm.id, 1)
        with pytest.raises(Forbidden):
            world.attach.execute(actor, norm.id, _staged(world), 1)

    stored = _read(world, norm.id)
    assert (stored.title, stored.archived, stored.file, stored.version) == (
        "Resolução sintética de teste",
        False,
        None,
        1,
    )
    with world.uow_factory() as uow:
        assert [n.code for n in uow.norms.list()] == ["RES-X-1"]
    assert _stored_files(world) == []
    assert len(world.audit_rows(norm.id)) == 1  # only the creation


# NBASE-10
def test_two_edits_from_the_same_version_accept_the_first_and_refuse_the_second(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())

    world.update.execute(world.admin, norm.id, _fields(title="Primeira edição"), 1)
    with pytest.raises(StaleVersion):
        world.update.execute(world.admin, norm.id, _fields(title="Segunda edição"), 1)
    with pytest.raises(StaleVersion):
        world.archive.execute(world.admin, norm.id, 1)
    with pytest.raises(StaleVersion):
        world.attach.execute(world.admin, norm.id, _staged(world), 1)

    stored = _read(world, norm.id)
    assert (stored.title, stored.archived, stored.file) == ("Primeira edição", False, None)
    assert _stored_files(world) == []  # the refused file did not stay on the disk


# NLIST-01, NLIST-02
def test_listing_hides_the_archived_norms_unless_asked_and_brings_the_linked_rules(world):
    seed_reference_data(world.uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(world.uow_factory())
    extra = world.create.execute(world.admin, "RES-ARQUIVADA-1", _fields(title="Arquivada"))
    world.archive.execute(world.admin, extra.id, 1)

    visible = {n.norm.code: n for n in world.list.execute(world.docente)}
    everything = {n.norm.code: n for n in world.list.execute(world.docente, True)}

    assert "RES-ARQUIVADA-1" not in visible
    assert everything["RES-ARQUIVADA-1"].norm.archived is True
    assert set(visible) | {"RES-ARQUIVADA-1"} == set(everything)
    assert {"LEI-12772-2012", "RES-4644-2015-CONSEPE", "TABELA-OFICIAL-UFPA"} <= set(visible)

    lei = visible["LEI-12772-2012"].rules
    assert [(r.kind, r.name) for r in lei] == [("CARREIRA", LEI_15141_2025.name)]
    res = visible["RES-4644-2015-CONSEPE"].rules
    assert [(r.kind, r.name) for r in res] == [("CARREIRA", RES_4644_2015.name)]
    manual = visible["MANUAL-PROGEP-PROGRESSAO"].rules
    assert [(r.kind, r.name) for r in manual] == [("TITULACAO", LEI_15141_2025.name)]
    assert "classe C: DOUTORADO" in manual[0].detail
    assert "classe D: DOUTORADO" in manual[0].detail
    table = visible["TABELA-OFICIAL-UFPA"].rules
    assert table
    assert {r.kind for r in table} == {"TABELA"}
    assert visible["IN-01-2026-IFCH"].rules == ()  # a norm no rule cites


def test_getting_a_norm_brings_its_rules_and_an_unknown_id_is_not_found(world):
    seed_reference_data(world.uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    with world.uow_factory() as uow:
        lei = uow.norms.get_by_code("LEI-12772-2012")

    found = world.get.execute(world.docente, lei.id)

    assert found.norm == lei
    assert [r.kind for r in found.rules] == ["CARREIRA"]
    with pytest.raises(NotFound):
        world.get.execute(world.docente, uuid.uuid4())


# Failure to store the file (design, Error Handling Strategy)
def test_a_failure_storing_the_new_file_leaves_the_record_and_the_previous_file_intact(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    first = world.attach.execute(world.admin, norm.id, _staged(world, "primeira.pdf"), 1)

    class BrokenStorage:
        def save(self, staged):
            raise OSError("disk full")

        def delete(self, internal_name):
            raise AssertionError("nothing was stored, nothing to delete")

    with pytest.raises(OSError):
        world.attach_with(BrokenStorage()).execute(
            world.admin, norm.id, _staged(world, "segunda.pdf"), first.version
        )

    assert _read(world, norm.id) == first
    assert _stored_files(world) == [first.file.internal_name]
    assert len(world.audit_rows(norm.id)) == 2  # creation and the first attachment only


def test_a_failure_after_storing_removes_the_new_file_and_keeps_the_previous_one(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    first = world.attach.execute(world.admin, norm.id, _staged(world, "primeira.pdf"), 1)

    class BrokenAudit:
        def record(self, *args, **kwargs):
            raise RuntimeError("audit down")

    broken = norm_cases.AttachNormFile(
        world.uow_factory, BrokenAudit(), world.storage, PillowFileInspector()
    )
    with pytest.raises(RuntimeError):
        broken.execute(world.admin, norm.id, _staged(world, "segunda.pdf"), first.version)

    assert _read(world, norm.id) == first
    assert _stored_files(world) == [first.file.internal_name]


# Download: open to every authenticated person, 404 without a file
def test_downloading_returns_the_stored_file_and_its_display_name_to_any_role(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())
    attached = world.attach.execute(world.admin, norm.id, _staged(world, "norma-x.pdf"), 1)

    for actor in (world.docente, world.secretaria, world.admin):
        path, name = world.download.execute(actor, norm.id)
        assert path == world.storage.open(attached.file.internal_name)
        assert path.read_bytes()[:5] == b"%PDF-"
        assert name == "norma-x.pdf"


def test_downloading_a_norm_without_a_file_or_an_unknown_norm_is_not_found(world):
    norm = world.create.execute(world.admin, "RES-X-1", _fields())

    with pytest.raises(NotFound):
        world.download.execute(world.docente, norm.id)
    with pytest.raises(NotFound):
        world.download.execute(world.docente, uuid.uuid4())


def test_editing_an_unknown_norm_is_not_found(world):
    with pytest.raises(NotFound):
        world.update.execute(world.admin, uuid.uuid4(), _fields(), 1)
