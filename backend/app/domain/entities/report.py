"""Report template and draft entities (REL-01, REL-07).

The template says which activities go to each section and how an entry reads; the draft holds
the text of each entry with its source. A draft is immutable: an edit builds a copy with
`dataclasses.replace`.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.entities.generated import GenerationAlert


class EntrySource(StrEnum):
    MODELO = "MODELO"
    IA = "IA"
    USUARIO = "USUARIO"


class GroupBy(StrEnum):
    ACADEMIC_PERIOD = "academic_period"
    ITEM = "item"
    NONE = "none"


@dataclass(frozen=True)
class MatchRule:
    """Activities of a scoring group, or of one item of it, that belong to a section."""

    group: int
    item: int | None = None


@dataclass(frozen=True)
class EntrySpec:
    """How an entry reads: one `line` or labeled `fields`, with markers such as `{title}`."""

    line: str | None = None
    fields: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if (self.line is None) == (not self.fields):
            raise ValueError("an entry has a line or fields, not both and not neither")


@dataclass(frozen=True)
class TemplateSection:
    key: str
    title: str
    match: tuple[MatchRule, ...]
    group_by: GroupBy
    entry: EntrySpec
    order_items: bool = False


@dataclass(frozen=True)
class ReportTemplate:
    id: str
    version: int
    sections: tuple[TemplateSection, ...]

    def section(self, key: str) -> TemplateSection | None:
        return next((s for s in self.sections if s.key == key), None)


@dataclass(frozen=True)
class DraftEntry:
    activity_id: UUID
    text: str
    source: EntrySource
    warnings: tuple[GenerationAlert, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", EntrySource(self.source))


@dataclass(frozen=True)
class DraftSection:
    key: str
    title: str
    free_text: str = ""
    entries: tuple[DraftEntry, ...] = ()
    warnings: tuple[GenerationAlert, ...] = ()


@dataclass(frozen=True)
class ReportDraft:
    process_id: UUID
    template_id: str
    template_version: int
    sections: tuple[DraftSection, ...]
    version: int
