"""Schemas of the board routes: the ordinance, the fields of the Parecer and the city of the
Requerimento (PORT-02, PORT-05, PAR-01, REQ-05).

The bodies refuse unknown fields (422). The limits of the values are checked by the use cases, so
a value over a limit is a 422 that names the field (PORT-11, PAR-13); nothing here carries the key
of the AI or the stored name of a file.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.application.use_cases.board import BoardView, MemberInput
from app.domain.entities.board import (
    BoardMember,
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
    OrdinanceFile,
    OrdinanceReadingCode,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ReadingState,
    RequestSettings,
    ValueSource,
)


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemberIn(_Body):
    name: str
    role: BoardRole


class OrdinanceDataIn(_Body):
    number: str | None = None
    ordinance_date: date | None = None
    members: list[MemberIn] = []
    expected_version: int

    def member_inputs(self) -> list[MemberInput]:
        return [MemberInput(member.name, member.role) for member in self.members]


class RereadIn(_Body):
    expected_version: int


class OpinionIn(_Body):
    conclusion: OpinionConclusion | None = None
    opinion_date: date | None = None
    place: str | None = None
    notes: str | None = None
    expected_version: int


class RequestSettingsIn(_Body):
    city: str | None = None
    expected_version: int


class MemberOut(BaseModel):
    name: str
    role: BoardRole
    page: int | None
    source: ValueSource

    @classmethod
    def of(cls, member: BoardMember) -> "MemberOut":
        return cls(name=member.name, role=member.role, page=member.page, source=member.source)


class OrdinanceFileOut(BaseModel):
    original_name: str
    mime: str
    size_bytes: int
    page_count: int | None
    deleted: bool

    @classmethod
    def of(cls, file: OrdinanceFile | None) -> "OrdinanceFileOut | None":
        if file is None:
            return None
        return cls(
            original_name=file.original_name,
            mime=file.mime,
            size_bytes=file.size_bytes,
            page_count=file.page_count,
            deleted=file.deleted_at is not None,
        )


class OrdinanceWarningOut(BaseModel):
    code: OrdinanceWarningCode
    field: str

    @classmethod
    def of(cls, warning: OrdinanceWarning) -> "OrdinanceWarningOut":
        return cls(code=warning.code, field=warning.field)


class OrdinanceOut(BaseModel):
    number: str | None
    number_page: int | None
    number_source: ValueSource | None
    ordinance_date: date | None
    date_page: int | None
    date_source: ValueSource | None
    members: list[MemberOut]
    file: OrdinanceFileOut | None
    reading_state: ReadingState
    reading_code: OrdinanceReadingCode | None
    warnings: list[OrdinanceWarningOut]
    version: int

    @classmethod
    def of(cls, ordinance: BoardOrdinance) -> "OrdinanceOut":
        return cls(
            number=ordinance.number,
            number_page=ordinance.number_page,
            number_source=ordinance.number_source,
            ordinance_date=ordinance.ordinance_date,
            date_page=ordinance.date_page,
            date_source=ordinance.date_source,
            members=[MemberOut.of(member) for member in ordinance.members],
            file=OrdinanceFileOut.of(ordinance.file),
            reading_state=ordinance.reading_state,
            reading_code=ordinance.reading_code,
            warnings=[OrdinanceWarningOut.of(warning) for warning in ordinance.warnings],
            version=ordinance.version,
        )


class OpinionOut(BaseModel):
    conclusion: OpinionConclusion | None
    opinion_date: date | None
    place: str | None
    notes: str | None
    version: int

    @classmethod
    def of(cls, opinion: BoardOpinion) -> "OpinionOut":
        return cls(
            conclusion=opinion.conclusion,
            opinion_date=opinion.opinion_date,
            place=opinion.place,
            notes=opinion.notes,
            version=opinion.version,
        )


class RequestSettingsOut(BaseModel):
    city: str | None
    version: int

    @classmethod
    def of(cls, settings: RequestSettings) -> "RequestSettingsOut":
        return cls(city=settings.city, version=settings.version)


class BoardOut(BaseModel):
    ordinance: OrdinanceOut
    opinion: OpinionOut
    request_settings: RequestSettingsOut

    @classmethod
    def of(cls, view: BoardView) -> "BoardOut":
        return cls(
            ordinance=OrdinanceOut.of(view.ordinance),
            opinion=OpinionOut.of(view.opinion),
            request_settings=RequestSettingsOut.of(view.request_settings),
        )
