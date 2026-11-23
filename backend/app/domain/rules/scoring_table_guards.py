"""Pure rules that block archiving a table, deleting a version or a table and editing the
criteria of a version (GTAB-20, GTAB-25, GTAB-27, GTAB-29, GTAB-42).

The codes and the texts live only here: the use cases, the table list and the screen read the
same ones. A blocker never decides alone how a request ends; the use cases refuse with 409 and
the code, and the preview of a deletion shows the same list before the click.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.domain.entities.scoring import ScoringTableVersion

OFFICIAL_TABLE_PROTECTED = "TABELA_OFICIAL_PROTEGIDA"
USED_BY_PROCESS = "VERSAO_USADA_POR_PROCESSO"
IN_USE_OF_UNIT = "VERSAO_EM_USO_DE_UNIDADE"
REPLACES_OTHER = "VERSAO_SUBSTITUI_OUTRA"
LAST_VERSION = "ULTIMA_VERSAO_DA_TABELA"
TABLE_WITH_VERSION_IN_USE = "TABELA_COM_VERSAO_EM_USO"
SUPERSEDED = "VERSAO_SUBSTITUIDA"
NOT_LATEST = "VERSAO_NAO_MAIS_RECENTE"


@dataclass(frozen=True)
class Blocker:
    code: str
    message: str
    count: int | None = None  # processes, when the blocker is about their use
    acronyms: tuple[str, ...] = ()  # units, when the blocker is about the version in use


@dataclass(frozen=True)
class VersionFacts:
    process_count: int  # processes (any status) that chose the version
    default_unit_acronyms: tuple[str, ...]  # units that have it as the version in use
    replaces_other: bool  # another version points to it as `superseded_by`
    is_superseded: bool
    has_later_version: bool  # some version of the table starts after it (superseded or not)
    is_only_version: bool
    table_archived: bool
    is_official: bool  # the table is the official one (by name); only its current versions count


@dataclass(frozen=True)
class TableFacts:
    is_official: bool
    process_count: int  # processes that chose any version of the table
    default_unit_acronyms: tuple[str, ...]  # units with a version of the table in use
    table_archived: bool


def has_later_version(
    version: ScoringTableVersion, versions_of_table: Collection[ScoringTableVersion]
) -> bool:
    """Whether some version of the table starts after this one, superseded ones included."""
    return any(other.valid_from > version.valid_from for other in versions_of_table)


def _acronyms(acronyms: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(acronyms))


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _official_version() -> Blocker:
    return Blocker(
        OFFICIAL_TABLE_PROTECTED,
        "A versão atual da tabela oficial da UFPA não pode ser excluída; "
        "só as versões substituídas podem ser excluídas",
    )


def _official_table() -> Blocker:
    return Blocker(
        OFFICIAL_TABLE_PROTECTED,
        "A tabela oficial da UFPA não pode ser excluída; arquive-a se não for mais usada",
    )


def version_delete_blockers(facts: VersionFacts) -> list[Blocker]:
    """Why the version cannot be deleted, in the order the use case answers (GTAB-27)."""
    blockers: list[Blocker] = []
    if facts.is_official and not facts.is_superseded:
        blockers.append(_official_version())
    if facts.process_count > 0:
        blockers.append(
            Blocker(
                USED_BY_PROCESS,
                "A versão é usada por "
                f"{_plural(facts.process_count, 'processo', 'processos')} "
                "e não pode ser excluída",
                count=facts.process_count,
            )
        )
    if facts.default_unit_acronyms:
        acronyms = _acronyms(facts.default_unit_acronyms)
        blockers.append(
            Blocker(
                IN_USE_OF_UNIT,
                f"A versão está em uso das unidades {', '.join(acronyms)}; marque outra "
                "versão ou desmarque-a antes de excluir",
                acronyms=acronyms,
            )
        )
    if facts.replaces_other:
        blockers.append(
            Blocker(
                REPLACES_OTHER,
                "A versão substitui outra versão da tabela e não pode ser excluída",
            )
        )
    if facts.is_only_version:
        blockers.append(
            Blocker(
                LAST_VERSION,
                'É a única versão da tabela; para removê-la use "Excluir tabela"',
            )
        )
    return blockers


def table_archive_blockers(facts: TableFacts) -> list[Blocker]:
    """Why the table cannot be archived (GTAB-25)."""
    if not facts.default_unit_acronyms:
        return []
    acronyms = _acronyms(facts.default_unit_acronyms)
    return [
        Blocker(
            TABLE_WITH_VERSION_IN_USE,
            f"A tabela tem versão em uso das unidades {', '.join(acronyms)}; marque outra "
            "tabela ou desmarque a versão antes de arquivar",
            acronyms=acronyms,
        )
    ]


def table_delete_blockers(facts: TableFacts) -> list[Blocker]:
    """Why the table cannot be deleted, in the order the use case answers (GTAB-29)."""
    blockers: list[Blocker] = []
    if facts.is_official:
        blockers.append(_official_table())
    if facts.process_count > 0:
        blockers.append(
            Blocker(
                USED_BY_PROCESS,
                "A tabela tem versões usadas por "
                f"{_plural(facts.process_count, 'processo', 'processos')} "
                "e não pode ser excluída",
                count=facts.process_count,
            )
        )
    if facts.default_unit_acronyms:
        acronyms = _acronyms(facts.default_unit_acronyms)
        blockers.append(
            Blocker(
                IN_USE_OF_UNIT,
                f"A tabela tem versão em uso das unidades {', '.join(acronyms)}; marque outra "
                "tabela ou desmarque a versão antes de excluir",
                acronyms=acronyms,
            )
        )
    return blockers


def criteria_read_only_reason(facts: VersionFacts) -> Blocker | None:
    """Why the criteria of the version cannot be edited, or None when they can (GTAB-20).

    The order is the one `UpdateVersionCriteria` always had: superseded, not the latest, used
    by a process.
    """
    if facts.is_superseded:
        return Blocker(
            SUPERSEDED,
            "Versão substituída é somente leitura; altere a versão que a substitui",
        )
    if facts.has_later_version:
        return Blocker(
            NOT_LATEST,
            "Versão anterior é somente leitura; altere a versão mais recente "
            "ou crie uma nova versão",
        )
    if facts.process_count > 0:
        return Blocker(
            USED_BY_PROCESS,
            "Versão já usada por processos não pode ser alterada; "
            "crie uma nova versão para alterar os critérios",
            count=facts.process_count,
        )
    return None
