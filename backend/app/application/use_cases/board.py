"""The board of a process: the ordinance (file, reading and data), the draft of the Parecer and the
city of the Requerimento (PORT-01 to PORT-12, PAR-01, PAR-12, PAR-13, REQ-05, BNAV-02, BNAV-03).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden; a
concluded or archived process refuses every write with 409 `PROCESSO_SOMENTE_LEITURA`. The
ordinance is not a `Document`: it creates no row in `documents` and never reaches the activities,
the score or the Comprovante (PORT-09). Audit events carry identifiers, states, counts and codes,
never the name of a board member (third party) and never a justification (regra 5).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.documents import (
    FILE_FIELD,
    MIME_BY_KIND,
    DocumentLimits,
    IncomingFile,
    UploadRejected,
)
from app.application.use_cases.generated_documents import _EditUseCase
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import (
    BoardMember,
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
    OrdinanceFile,
    ReadingState,
    RequestSettings,
    ValueSource,
)
from app.domain.entities.generated import GenerationCode
from app.domain.entities.user import User
from app.domain.errors import Conflict, Gone, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import Clock, FileInspector, FileStorage, UnitOfWork
from app.domain.rules.board_rules import validate_board_data, validate_city, validate_opinion_fields
from app.domain.rules.ordinance_grounding import DATE, MEMBERS, NUMBER
from app.domain.rules.upload_validation import extension_of, safe_display_name, validate_upload

BOARD_ENTITY = "board_ordinance"
_IN_PROGRESS = (ReadingState.PENDENTE, ReadingState.LENDO)


def _stale() -> StaleVersion:
    return StaleVersion(
        "A portaria foi alterada por outro usuário; recarregue",
        GenerationCode.VERSAO_DESATUALIZADA.value,
    )


def _file_view(file: OrdinanceFile | None) -> dict:
    """Name, hash and size of the file; the audit never carries what is inside it."""
    if file is None:
        return {}
    return {
        "original_name": file.original_name,
        "sha256": file.sha256,
        "size_bytes": file.size_bytes,
    }


def _state_view(ordinance: BoardOrdinance | None) -> dict:
    if ordinance is None:
        return {}
    return {
        "version": ordinance.version,
        "reading_state": ordinance.reading_state,
        **_file_view(ordinance.file),
    }


class _BoardUseCase(_EditUseCase):
    def _record(
        self,
        uow: UnitOfWork,
        actor: User,
        process_id: UUID,
        action: AuditAction,
        operation: str,
        before: dict,
        after: dict,
    ) -> None:
        self._audit.record(
            uow,
            actor.id,
            BOARD_ENTITY,
            process_id,
            action,
            before,
            {**after, "operation": operation},
        )


class UploadOrdinance(_BoardUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
        inspector: FileInspector,
        clock: Clock,
        limits: DocumentLimits | None = None,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock
        self._storage = storage
        self._inspector = inspector
        self._limits = limits or DocumentLimits()

    def execute(
        self,
        actor: User,
        process_id: UUID,
        incoming: IncomingFile,
        expected_version: int,
        replace: bool,
    ) -> BoardOrdinance:
        """Stores the file, queues the reading and audits (PORT-01).

        An ordinance that already has a file asks for `replace` (409 `PORTARIA_EXISTENTE`), and
        the old file leaves the disk only after the commit (PORT-08); an ordinance with only typed
        data takes the first file without it. `expected_version` is 0 when there is no ordinance.
        """
        stored: str | None = None
        try:
            with self._uow_factory() as uow:
                self._editable(uow, actor, process_id)
                facts = self._inspector.inspect(incoming.path)
                extension = extension_of(incoming.original_name)
                rejections = validate_upload(
                    facts, incoming.declared_mime, extension, self._limits.for_validation()
                )
                if rejections:
                    raise UploadRejected(rejections[0].code, rejections[0].message)
                current = uow.board.get(process_id)
                if (current.version if current else 0) != expected_version:
                    raise _stale()
                has_file = current is not None and (
                    current.file is not None and current.file.deleted_at is None
                )
                if has_file and not replace:
                    raise Conflict(
                        "O processo já tem uma portaria da banca enviada; confirme a substituição",
                        GenerationCode.PORTARIA_EXISTENTE.value,
                    )
                stored = self._storage.save(process_id, extension, incoming.path.read_bytes())
                file = OrdinanceFile(
                    internal_name=stored,
                    original_name=safe_display_name(incoming.original_name),
                    mime=MIME_BY_KIND[facts.kind],
                    size_bytes=incoming.size_bytes,
                    sha256=incoming.sha256,
                    page_count=facts.page_count or 1,
                )
                with self._versioned():
                    version = expected_version
                    if current is None:
                        version = uow.board.create(
                            BoardOrdinance(process_id), actor.id, expected_version
                        ).version
                    previous = uow.board.set_file(
                        process_id, file, actor.id, version, self._clock.now()
                    )
                result = uow.board.get(process_id)
                self._record(
                    uow,
                    actor,
                    process_id,
                    AuditAction.UPDATE if current else AuditAction.CREATE,
                    "REPLACE" if has_file else "UPLOAD",
                    _state_view(current),
                    _state_view(result),
                )
                uow.commit()
        except Exception:
            if stored is not None:
                self._storage.delete(process_id, stored)
            raise
        if previous is not None:
            self._storage.delete(process_id, previous.internal_name)
        return result


class RereadOrdinance(_BoardUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        clock: Clock,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock

    def execute(self, actor: User, process_id: UUID, expected_version: int) -> BoardOrdinance:
        """Ler de novo: a finished reading goes back to the queue (PORT-07). Without a file it
        is a 422 on `arquivo`; while the reading is queued or running it is a 409
        `OPERACAO_EM_ANDAMENTO`."""
        with self._uow_factory() as uow:
            self._editable(uow, actor, process_id)
            current = uow.board.get(process_id)
            if current is None or current.file is None or current.file.deleted_at is not None:
                raise ValidationFailed(FILE_FIELD, "A portaria não tem arquivo para ler")
            if current.version != expected_version:
                raise _stale()
            busy = Conflict(
                "A leitura da portaria já está em andamento",
                GenerationCode.OPERACAO_EM_ANDAMENTO.value,
            )
            if current.reading_state in _IN_PROGRESS:
                raise busy
            try:
                with self._versioned():
                    uow.board.request_reading(process_id, expected_version, self._clock.now())
            except StaleVersion:
                raise
            except Conflict:
                raise busy from None  # it was queued between the read and the lock
            result = uow.board.get(process_id)
            self._record(
                uow,
                actor,
                process_id,
                AuditAction.UPDATE,
                "REREAD",
                _state_view(current),
                _state_view(result),
            )
            uow.commit()
        return result


@dataclass(frozen=True)
class MemberInput:
    """A member as the person typed it: page and origin are decided here, not by the caller."""

    name: str
    role: BoardRole


def _typed_members(
    current: Sequence[BoardMember], typed: Sequence[MemberInput]
) -> tuple[BoardMember, ...]:
    """A member the person did not touch (same name and function) keeps its page and origin; any
    other is `INFORMADO` with no page."""
    known = {(m.name, m.role): m for m in current}
    return tuple(
        known.get((name, member.role))
        or BoardMember(name, member.role, None, ValueSource.INFORMADO)
        for member in typed
        for name in (member.name.strip(),)
    )


def _audit_view(ordinance: BoardOrdinance | None) -> dict:
    """Number, date and the count of members: never a name (third party)."""
    if ordinance is None:
        return {}
    return {
        "number": ordinance.number,
        "ordinance_date": ordinance.ordinance_date,
        "member_count": len(ordinance.members),
    }


class SaveOrdinanceData(_BoardUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        number: str | None,
        ordinance_date: date | None,
        members: Sequence[MemberInput],
        expected_version: int,
    ) -> BoardOrdinance:
        """Saves what the person typed; only the fields that changed become `INFORMADO` (PORT-05).

        Without an ordinance the save creates one with no file, everything typed that has a value
        (PORT-06), and needs `expected_version` 0. Limits are a 422 on the field (PORT-11), a
        version that is not the stored one is a 409 `VERSAO_DESATUALIZADA` (PORT-12).
        """
        number = (number or "").strip() or None
        with self._uow_factory() as uow:
            self._editable(uow, actor, process_id)
            current = uow.board.get(process_id)
            new_members = _typed_members(current.members if current else (), members)
            if errors := validate_board_data(number, new_members):
                first = errors[0]
                raise ValidationFailed(first.field, first.message, first.code)
            changed = _changed_fields(current, number, ordinance_date, new_members)
            with self._versioned():
                if current is None:
                    result = uow.board.create(
                        _created(process_id, number, ordinance_date, new_members),
                        actor.id,
                        expected_version,
                    )
                else:
                    result = uow.board.save_data(
                        _edited(current, number, ordinance_date, new_members, changed),
                        actor.id,
                        expected_version,
                    )
            self._record(
                uow,
                actor,
                process_id,
                AuditAction.UPDATE if current else AuditAction.CREATE,
                "SAVE",
                _audit_view(current),
                {**_audit_view(result), "fields_changed": changed},
            )
            uow.commit()
        return result


def _changed_fields(
    current: BoardOrdinance | None,
    number: str | None,
    ordinance_date: date | None,
    members: tuple[BoardMember, ...],
) -> list[str]:
    if current is None:
        return [
            name
            for name, value in ((NUMBER, number), (DATE, ordinance_date), (MEMBERS, members))
            if value
        ]
    return [
        name
        for name, now, before in (
            (NUMBER, number, current.number),
            (DATE, ordinance_date, current.ordinance_date),
            (MEMBERS, members, current.members),
        )
        if now != before
    ]


def _created(
    process_id: UUID,
    number: str | None,
    ordinance_date: date | None,
    members: tuple[BoardMember, ...],
) -> BoardOrdinance:
    typed = ValueSource.INFORMADO
    return BoardOrdinance(
        process_id,
        number=number,
        number_source=typed if number is not None else None,
        ordinance_date=ordinance_date,
        date_source=typed if ordinance_date is not None else None,
        members=members,
    )


def _edited(
    current: BoardOrdinance,
    number: str | None,
    ordinance_date: date | None,
    members: tuple[BoardMember, ...],
    changed: Sequence[str],
) -> BoardOrdinance:
    """The warning of a field the person changed describes a value that is gone: it is dropped."""
    edited = replace(
        current,
        members=members,
        warnings=tuple(w for w in current.warnings if w.field not in changed),
    )
    if NUMBER in changed:
        edited.number, edited.number_page = number, None
        edited.number_source = ValueSource.INFORMADO
    if DATE in changed:
        edited.ordinance_date, edited.date_page = ordinance_date, None
        edited.date_source = ValueSource.INFORMADO
    return edited


FILE_DELETED_MESSAGE = "O arquivo da portaria foi excluído na conclusão do processo"


@dataclass(frozen=True)
class BoardView:
    """The three things of the board, each with its own version; one that was never saved comes
    back empty with version 0, which is the `expected_version` of its first save. Nothing is
    filled in from the score: the conclusion stays empty until a person chooses it (PAR-12)."""

    ordinance: BoardOrdinance
    opinion: BoardOpinion
    request_settings: RequestSettings


class GetBoard(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> BoardView:
        """A read never writes."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            return BoardView(
                ordinance=uow.board.get(process_id) or BoardOrdinance(process_id, version=0),
                opinion=uow.opinions.get(process_id) or BoardOpinion(process_id, version=0),
                request_settings=uow.request_settings.get(process_id)
                or RequestSettings(process_id, version=0),
            )


@dataclass(frozen=True)
class OrdinanceDownload:
    path: Path
    name: str  # original name, display text only
    mime: str


class DownloadOrdinanceFile(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._storage = storage

    def execute(self, actor: User, process_id: UUID) -> OrdinanceDownload:
        """The stored file; `NotFound` without one, `Gone` once the conclusion removed it."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            ordinance = uow.board.get(process_id)
        file = ordinance.file if ordinance else None
        if file is None:
            raise NotFound("A portaria não tem arquivo")
        if file.deleted_at is not None:
            raise Gone(GenerationCode.ARQUIVO_EXCLUIDO.value, FILE_DELETED_MESSAGE)
        path = self._storage.path(process_id, file.internal_name)
        if not path.is_file():
            raise NotFound("Arquivo não encontrado")
        return OrdinanceDownload(path, file.original_name, file.mime)


OPINION_ENTITY = "board_opinion"
SETTINGS_ENTITY = "request_settings"


def _length(text: str | None) -> int:
    return len(text) if text else 0


class SaveOpinion(_BoardUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        conclusion: OpinionConclusion | None,
        opinion_date: date | None,
        place: str | None,
        expected_version: int,
    ) -> BoardOpinion:
        """Saves the fields the person fills for the Parecer (PAR-01). The conclusion is exactly
        what was sent, `None` included: the system never chooses or suggests one (PAR-12). The
        first save needs `expected_version` 0; the limit of the place is a 422 on the field
        (PMOD-29)."""
        place = (place or "").strip() or None
        with self._uow_factory() as uow:
            self._editable(uow, actor, process_id)
            if errors := validate_opinion_fields(place):
                raise ValidationFailed(errors[0].field, errors[0].message)
            current = uow.opinions.get(process_id)
            draft = BoardOpinion(process_id, conclusion, opinion_date, place)
            with self._versioned():
                if current is None:
                    result = uow.opinions.create(draft, actor.id, expected_version)
                else:
                    result = uow.opinions.update(draft, actor.id, expected_version)
            self._audit.record(
                uow,
                actor.id,
                OPINION_ENTITY,
                process_id,
                AuditAction.UPDATE if current else AuditAction.CREATE,
                self._view(current),
                self._view(result),
            )
            uow.commit()
        return result

    @staticmethod
    def _view(opinion: BoardOpinion | None) -> dict:
        """The code and the date of the choice and the size of the place, never the text."""
        if opinion is None:
            return {}
        return {
            "conclusion": opinion.conclusion,
            "opinion_date": opinion.opinion_date,
            "place_length": _length(opinion.place),
        }


class SaveRequestSettings(_BoardUseCase):
    def execute(
        self, actor: User, process_id: UUID, city: str | None, expected_version: int
    ) -> RequestSettings:
        """Saves the city of the Requerimento (REQ-05). It lives in `request_settings`, not in the
        process, so it never asks for the justification of the Etapa 1."""
        city = (city or "").strip() or None
        with self._uow_factory() as uow:
            self._editable(uow, actor, process_id)
            if errors := validate_city(city):
                raise ValidationFailed(errors[0].field, errors[0].message)
            current = uow.request_settings.get(process_id)
            draft = RequestSettings(process_id, city)
            with self._versioned():
                if current is None:
                    result = uow.request_settings.create(draft, expected_version)
                else:
                    result = uow.request_settings.update(draft, expected_version)
            self._audit.record(
                uow,
                actor.id,
                SETTINGS_ENTITY,
                process_id,
                AuditAction.UPDATE if current else AuditAction.CREATE,
                {"city_length": _length(current.city)} if current else {},
                {"city_length": _length(result.city)},
            )
            uow.commit()
        return result
