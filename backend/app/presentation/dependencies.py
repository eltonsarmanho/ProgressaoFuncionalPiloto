"""Composition root for request handlers (AD-001: wiring happens only here and in main)."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import Engine

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.auth import GetCurrentSession, Login, Logout
from app.application.use_cases.career import (
    CreateCareerVersion,
    ListCareerVersions,
    UpdateCareerVersion,
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
    GetScoringVersion,
    ListScoringTables,
    ListTableVersions,
)
from app.application.use_cases.units import ArchiveUnit, CreateUnit, ListUnits, UpdateUnit
from app.application.use_cases.users import CreateUser, ListUsers
from app.core.config import Settings
from app.domain.entities.user import Session, User
from app.domain.repositories.ports import Clock, UnitOfWork
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from app.infrastructure.security import tokens
from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher


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
    suggest_scoring_table: SuggestScoringTable
    choose_process_table: ChooseProcessTable
    calculate_process_score: CalculateProcessScore
    create_activity: CreateActivity
    get_activity: GetActivity
    list_activities: ListActivities
    update_activity: UpdateActivity
    change_activity_status: ChangeActivityStatus
    mark_activities_distinct: MarkActivitiesDistinct


def build_container(settings: Settings, engine: Engine, clock: Clock) -> Container:
    session_factory = make_session_factory(engine)

    def uow_factory() -> UnitOfWork:
        return SqlUnitOfWork(session_factory)

    hasher = Argon2PasswordHasher()
    audit = AuditService(clock)
    policy = AccessPolicy()
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
        suggest_scoring_table=SuggestScoringTable(uow_factory, audit, policy),
        choose_process_table=ChooseProcessTable(uow_factory, audit, policy),
        calculate_process_score=CalculateProcessScore(uow_factory, audit, policy),
        create_activity=CreateActivity(uow_factory, audit, policy),
        get_activity=GetActivity(uow_factory, audit, policy),
        list_activities=ListActivities(uow_factory, audit, policy),
        update_activity=UpdateActivity(uow_factory, audit, policy),
        change_activity_status=ChangeActivityStatus(uow_factory, audit, policy),
        mark_activities_distinct=MarkActivitiesDistinct(uow_factory, audit, policy),
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def current_user(request: Request) -> User:
    """Set by the auth middleware for every protected /api route."""
    return request.state.user


def current_session(request: Request) -> Session:
    return request.state.session
