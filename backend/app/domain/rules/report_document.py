"""The report document: the draft, the header and the layout put together for the writers
(REL-09, REL-11, REL-12).

Pure. The text of every entry is the text of the draft; this function only decides where it goes
(section, subtitle, order) and writes the header and the identification from the process. A
section with no entry and no typed text is left out.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.entities.activity import Activity
from app.domain.entities.report import (
    DocumentGroup,
    DocumentSection,
    DraftSection,
    GroupBy,
    ReportDocument,
    ReportDraft,
    TemplateSection,
)
from app.domain.rules.pt_format import format_interstice, format_period
from app.domain.rules.report_draft import GroupMap, ReportConfig, document_sections, group_target
from app.domain.rules.scoring_periods import is_start_only
from app.domain.rules.table_document import TableHeader, roman

_MARKER = re.compile(r"\{(\w+)\}")
ONGOING = "em andamento"


def _markers(header: TableHeader) -> dict[str, str]:
    return {
        "unit_name": header.unit_name,
        "professor_name": header.professor_name,
        "current_class": header.current_class,
        "current_level": str(header.current_level),
        "target_class": header.target_class,
        "target_level": str(header.target_level),
        "interstice": format_interstice(header.interstice),
    }


def _fill(line: str, values: Mapping[str, str]) -> str:
    return _MARKER.sub(lambda found: values.get(found.group(1), found.group(0)), line)


@dataclass(frozen=True)
class _Placed:
    """An entry text with the subtitle it goes under and the key that orders the subtitles."""

    subtitle: str | None
    order: tuple
    text: str


def _subtitle(
    spec: TemplateSection,
    activity: Activity | None,
    group_map: GroupMap,
    item_names: Mapping[tuple[int, int], str],
) -> tuple[str | None, tuple]:
    """The subtitle of an entry and how the subtitles are ordered inside the section."""
    if activity is None:
        return None, (1,)
    if spec.group_by is GroupBy.ACADEMIC_PERIOD:
        period = activity.academic_period
        return (format_period(period) if period else None), (period is None, period or "")
    if spec.group_by is GroupBy.ITEM:
        group, item = activity.group_number, activity.item_number
        name = item_names.get((group, item)) or f"{roman(group)}.{item}"
        ongoing = spec.order_items and is_start_only(activity)
        return (f"{name} ({ONGOING})" if ongoing else name), (group, item, ongoing)
    target = group_target(group_map, activity)
    if target is not None and target.section_key == spec.key:
        return target.subtitle, (0,)
    return None, (1,)  # an activity moved here keeps no subtitle of its old section


def _section(
    section: DraftSection,
    spec: TemplateSection,
    activities: Mapping,
    group_map: GroupMap,
    item_names: Mapping[tuple[int, int], str],
) -> DocumentSection:
    placed = []
    for entry in section.entries:
        if not entry.text.strip():
            continue
        subtitle, order = _subtitle(spec, activities.get(entry.activity_id), group_map, item_names)
        placed.append(_Placed(subtitle, order, entry.text.strip()))
    if spec.group_by is not GroupBy.NONE:
        placed.sort(key=lambda p: p.order)  # stable: the draft order holds inside a subtitle
    grouped: dict[str | None, list[str]] = {}
    for item in placed:
        grouped.setdefault(item.subtitle, []).append(item.text)
    groups = tuple(DocumentGroup(subtitle, tuple(texts)) for subtitle, texts in grouped.items())
    return DocumentSection(section.key, section.title, section.free_text.strip(), groups)


def build_report_document(
    config: ReportConfig,
    header: TableHeader,
    draft: ReportDraft,
    activities: Sequence[Activity],
    item_names: Mapping[tuple[int, int], str] | None = None,
) -> ReportDocument:
    """`item_names` maps (group, item) to the name of the criterion, for the subtitles of the
    sections grouped by item; without it the subtitle is the numeral of the item."""
    values = _markers(header)
    by_id = {a.id: a for a in activities}
    sections = []
    for draft_section in document_sections(draft):
        spec = config.template.section(draft_section.key)
        if spec is None:
            continue
        section = _section(draft_section, spec, by_id, config.group_map, item_names or {})
        if section.free_text or section.groups:
            sections.append(section)
    layout = config.layout
    return ReportDocument(
        layout=layout,
        header_lines=tuple(_fill(line, values) for line in layout.header_lines),
        title=layout.title,
        identification=tuple(_fill(line, values) for line in layout.identification),
        body_heading=layout.body_heading,
        sections=tuple(sections),
    )
