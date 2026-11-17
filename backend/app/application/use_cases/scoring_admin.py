"""Scoring table catalog use cases (TAB-08); administration use cases are added in phase 6."""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.scoring import ScoringTableVersion
from app.domain.errors import NotFound
from app.domain.repositories.ports import ScoringTableRecord, UnitOfWork


@dataclass(frozen=True)
class VersionView:
    version: ScoringTableVersion
    in_use: bool


@dataclass(frozen=True)
class TableView:
    table: ScoringTableRecord
    versions: list[VersionView]


def _views(uow: UnitOfWork, versions) -> list[VersionView]:
    return [VersionView(v, uow.scoring_tables.version_in_use(v.id)) for v in versions]


class ListScoringTables:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self) -> list[TableView]:
        with self._uow_factory() as uow:
            return [
                TableView(t, _views(uow, uow.scoring_tables.list_versions(t.id)))
                for t in uow.scoring_tables.list_tables()
            ]


class ListTableVersions:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, table_id: UUID) -> list[VersionView]:
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            return _views(uow, uow.scoring_tables.list_versions(table_id))


class GetScoringVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, version_id: UUID) -> VersionView:
        with self._uow_factory() as uow:
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise NotFound("Versão da tabela de pontuação não encontrada")
            return _views(uow, [version])[0]
