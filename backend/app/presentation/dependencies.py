"""Composition root for request handlers (AD-001: wiring happens only here and in main)."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import Engine

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.document_analyzer import DocumentAnalyzer
from app.application.use_cases.auth import GetCurrentSession, Login, Logout
from app.application.use_cases.career import (
    CreateCareerVersion,
    ListCareerVersions,
    UpdateCareerVersion,
)
from app.application.use_cases.document_processing import ProcessDocument, RecoverStuckJobs
from app.application.use_cases.documents import (
    ClassifyDocumentManually,
    DeleteDocument,
    DocumentLimits,
    DownloadDocument,
    GetDocument,
    ListDocuments,
    ReplaceDocument,
    ReprocessDocument,
    UploadDocuments,
)
from app.application.use_cases.processes import (
    ChangeProcessStatus,
    CreateProcess,
    GetProcess,
    GetProcessHistory,
    ListProcesses,
    UpdateProcess,
)
from app.application.use_cases.professors import (
    ArchiveProfessor,
    CreateProfessor,
    GetProfessor,
    ListProfessors,
    UpdateProfessor,
)
from app.application.use_cases.scoring import (
    CalculateProcessScore,
    ChangeActivityStatus,
    ChooseProcessTable,
    CreateActivity,
    GetActivity,
    ListActivities,
    MarkActivitiesDistinct,
    SuggestScoringTable,
    UpdateActivity,
)
from app.application.use_cases.scoring_admin import (
    CreateScoringTable,
    CreateVersionFrom,
    DuplicateScoringTable,
    GetScoringVersion,
    GetTableHistory,
    ImportCriteriaCsv,
    ListScoringTables,
    ListTableVersions,
    SetTableUnits,
    UpdateVersionCriteria,
)
from app.application.use_cases.units import ArchiveUnit, CreateUnit, ListUnits, UpdateUnit
from app.application.use_cases.users import CreateUser, ListUsers
from app.core.config import Settings
from app.domain.entities.user import Session, User
from app.domain.repositories.ports import (
    AiExtractor,
    Clock,
    FileInspector,
    FileStorage,
    TextExtractor,
    UnitOfWork,
)
from app.infrastructure.ai.maritalk import MariTalkExtractor
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from app.infrastructure.files.inspector import PillowFileInspector
from app.infrastructure.ocr.extractor import DocumentTextExtractor
from app.infrastructure.security import tokens
from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.storage.local_storage import LocalFileStorage


@dataclass
class Container:
    settings: Settings
    engine: Engine
    clock: Clock
    uow_factory: Callable[[], UnitOfWork]
    login: Login
    logout: Logout
    current_session: GetCurrentSession
    create_user: CreateUser
    list_users: ListUsers
    list_units: ListUnits
    create_unit: CreateUnit
    update_unit: UpdateUnit
    archive_unit: ArchiveUnit
    create_professor: CreateProfessor
    update_professor: UpdateProfessor
    archive_professor: ArchiveProfessor
    get_professor: GetProfessor
    list_professors: ListProfessors
    create_process: CreateProcess
    get_process: GetProcess
    list_processes: ListProcesses
    update_process: UpdateProcess
    change_process_status: ChangeProcessStatus
    process_history: GetProcessHistory
    list_career_versions: ListCareerVersions
    create_career_version: CreateCareerVersion
    update_career_version: UpdateCareerVersion
    list_scoring_tables: ListScoringTables
    list_table_versions: ListTableVersions
    get_scoring_version: GetScoringVersion
    create_scoring_table: CreateScoringTable
    duplicate_scoring_table: DuplicateScoringTable
    create_scoring_version: CreateVersionFrom
    update_version_criteria: UpdateVersionCriteria
    import_criteria_csv: ImportCriteriaCsv
    set_table_units: SetTableUnits
    table_history: GetTableHistory
    suggest_scoring_table: SuggestScoringTable
    choose_process_table: ChooseProcessTable
    calculate_process_score: CalculateProcessScore
    create_activity: CreateActivity
    get_activity: GetActivity
    list_activities: ListActivities
    update_activity: UpdateActivity
    change_activity_status: ChangeActivityStatus
    mark_activities_distinct: MarkActivitiesDistinct
    storage: FileStorage
    inspector: FileInspector
    process_document: ProcessDocument
    recover_stuck_jobs: RecoverStuckJobs
    upload_documents: UploadDocuments
    list_documents: ListDocuments
    get_document: GetDocument
    download_document: DownloadDocument
    replace_document: ReplaceDocument
    delete_document: DeleteDocument
    reprocess_document: ReprocessDocument
    classify_document: ClassifyDocumentManually


def build_container(
    settings: Settings,
    engine: Engine,
    clock: Clock,
    ai_extractor: AiExtractor | None = None,
    text_extractor: TextExtractor | None = None,
) -> Container:
    """Wires every service; the document services are shared by the routes and the worker.

    Tests pass a fake `ai_extractor` or `text_extractor`; production builds the MariTalk
    adapter and the PyMuPDF plus Tesseract reader (AD-005, AD-009).
    """
    session_factory = make_session_factory(engine)

    def uow_factory() -> UnitOfWork:
        return SqlUnitOfWork(session_factory)

    hasher = Argon2PasswordHasher()
    audit = AuditService(clock)
    policy = AccessPolicy()
    create_activity = CreateActivity(uow_factory, audit, policy)
    change_status = ChangeActivityStatus(uow_factory, audit, policy)
    storage = LocalFileStorage(settings.storage_dir)
    inspector = PillowFileInspector(settings.max_megapixels)
    limits = DocumentLimits(
        max_file_bytes=settings.max_upload_mb * 1024 * 1024,
        max_pages=settings.max_pages,
        max_megapixels=settings.max_megapixels,
        max_documents_per_process=settings.max_documents_per_process,
        max_uploads_per_minute=settings.max_uploads_per_minute,
    )
    analyzer = DocumentAnalyzer(
        text_extractor or DocumentTextExtractor(clock),
        ai_extractor or MariTalkExtractor(settings),
        clock,
    )
    return Container(
        settings=settings,
        engine=engine,
        clock=clock,
        uow_factory=uow_factory,
        login=Login(uow_factory, hasher, tokens, clock),
        logout=Logout(uow_factory, tokens),
        current_session=GetCurrentSession(uow_factory, tokens, clock),
        create_user=CreateUser(uow_factory, hasher, audit),
        list_users=ListUsers(uow_factory),
        list_units=ListUnits(uow_factory),
        create_unit=CreateUnit(uow_factory, audit),
        update_unit=UpdateUnit(uow_factory, audit),
        archive_unit=ArchiveUnit(uow_factory, audit),
        create_professor=CreateProfessor(uow_factory, audit, policy),
        update_professor=UpdateProfessor(uow_factory, audit, policy),
        archive_professor=ArchiveProfessor(uow_factory, audit, policy),
        get_professor=GetProfessor(uow_factory, audit, policy),
        list_professors=ListProfessors(uow_factory, audit, policy),
        create_process=CreateProcess(uow_factory, audit, policy),
        get_process=GetProcess(uow_factory, audit, policy),
        list_processes=ListProcesses(uow_factory, audit, policy),
        update_process=UpdateProcess(uow_factory, audit, policy),
        change_process_status=ChangeProcessStatus(uow_factory, audit, policy),
        process_history=GetProcessHistory(uow_factory, audit, policy),
        list_career_versions=ListCareerVersions(uow_factory),
        create_career_version=CreateCareerVersion(uow_factory, audit),
        update_career_version=UpdateCareerVersion(uow_factory, audit),
        list_scoring_tables=ListScoringTables(uow_factory),
        list_table_versions=ListTableVersions(uow_factory),
        get_scoring_version=GetScoringVersion(uow_factory),
        create_scoring_table=CreateScoringTable(uow_factory, audit),
        duplicate_scoring_table=DuplicateScoringTable(uow_factory, audit),
        create_scoring_version=CreateVersionFrom(uow_factory, audit),
        update_version_criteria=UpdateVersionCriteria(uow_factory, audit),
        import_criteria_csv=ImportCriteriaCsv(uow_factory, audit),
        set_table_units=SetTableUnits(uow_factory, audit),
        table_history=GetTableHistory(uow_factory),
        suggest_scoring_table=SuggestScoringTable(uow_factory, audit, policy),
        choose_process_table=ChooseProcessTable(uow_factory, audit, policy),
        calculate_process_score=CalculateProcessScore(uow_factory, audit, policy),
        create_activity=create_activity,
        get_activity=GetActivity(uow_factory, audit, policy),
        list_activities=ListActivities(uow_factory, audit, policy),
        update_activity=UpdateActivity(uow_factory, audit, policy),
        change_activity_status=change_status,
        mark_activities_distinct=MarkActivitiesDistinct(uow_factory, audit, policy),
        storage=storage,
        inspector=inspector,
        process_document=ProcessDocument(uow_factory, audit, storage, analyzer, create_activity),
        recover_stuck_jobs=RecoverStuckJobs(uow_factory),
        upload_documents=UploadDocuments(
            uow_factory, audit, policy, storage, inspector, clock, limits
        ),
        list_documents=ListDocuments(uow_factory, audit, policy),
        get_document=GetDocument(uow_factory, audit, policy),
        download_document=DownloadDocument(uow_factory, audit, policy, storage),
        replace_document=ReplaceDocument(
            uow_factory, audit, policy, storage, inspector, clock, change_status, limits
        ),
        delete_document=DeleteDocument(uow_factory, audit, policy, storage),
        reprocess_document=ReprocessDocument(uow_factory, audit, policy, change_status),
        classify_document=ClassifyDocumentManually(uow_factory, audit, policy),
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def current_user(request: Request) -> User:
    """Set by the auth middleware for every protected /api route."""
    return request.state.user


def current_session(request: Request) -> Session:
    return request.state.session
