"""Report template and draft entities (REL-01, REL-07).

The template says which activities go to each section and how an entry reads; the draft holds
the text of each entry with its source. A draft is immutable: an edit builds a copy with
`dataclasses.replace`.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.entities.generated import DocumentKind, GenerationAlert


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


@dataclass(frozen=True)
class PageSetup:
    """Page of the report: A4 with the margins and the font of the institutional model."""

    margin_left_mm: float
    margin_right_mm: float
    margin_top_mm: float
    margin_bottom_mm: float
    font_name: str
    font_size_pt: float
    size: str = "A4"


@dataclass(frozen=True)
class ReportLayout:
    """What the template says about the document outside the sections.

    `header_lines`, `title` and `identification` are texts with markers (`{unit_name}`,
    `{professor_name}`, `{current_class}`, `{current_level}`, `{target_class}`, `{target_level}`,
    `{interstice}`) that the document model fills; `body_heading` opens the sections.
    """

    page: PageSetup
    header_lines: tuple[str, ...]
    title: str
    identification: tuple[str, ...]
    body_heading: str
    entry_style: str


@dataclass(frozen=True)
class DossierItem:
    """One document of the dossier, in delivery order; `generated_by` is set for the ones the
    system produces (ORD-01)."""

    order: int
    title: str
    generated_by: DocumentKind | None = None
