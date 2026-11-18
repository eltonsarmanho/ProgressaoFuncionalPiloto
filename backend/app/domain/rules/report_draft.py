"""Rascunho do Relatório: distribution of the activities by section and its order (REL-01, REL-02).

Pure functions. The group map is configuration: it says to which section an activity goes and,
for a section that gathers several groups, under which subtitle. The draft keeps entries in the
order of the section; the writers read subtitles, periods and modalities from the activities.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.report import (
    DraftEntry,
    DraftSection,
    EntrySource,
    GroupBy,
    MatchRule,
    ReportDraft,
    ReportTemplate,
    TemplateSection,
)
from app.domain.rules.activity_order import eligible_activities, table_order
from app.domain.rules.scoring_periods import is_start_only


@dataclass(frozen=True)
class GroupTarget:
    """The section an activity goes to and the subtitle it carries there, when it has one."""

    section_key: str
    subtitle: str | None = None


GroupMap = Mapping[MatchRule, GroupTarget]


def group_target(group_map: GroupMap, activity: Activity) -> GroupTarget | None:
    """The rule of the item, or else the rule of the whole group; None when neither exists."""
    if activity.group_number is None:
        return None
    return group_map.get(MatchRule(activity.group_number, activity.item_number)) or group_map.get(
        MatchRule(activity.group_number)
    )


def _sort_key(section: TemplateSection, activity: Activity):
    """Order inside a section: by academic period, by item with the ongoing last, or the table's."""
    base = table_order(activity)
    if section.group_by is GroupBy.ACADEMIC_PERIOD:
        return (activity.academic_period is None, activity.academic_period or "", *base)
    if section.group_by is GroupBy.ITEM and section.order_items:
        return (*base[:2], is_start_only(activity), *base[2:])
    return base


def _new_entry(activity: Activity) -> DraftEntry:
    return DraftEntry(activity.id, activity.title, EntrySource.MODELO)


def propose_draft(
    template: ReportTemplate,
    activities: Sequence[Activity],
    group_map: GroupMap,
    *,
    process_id: UUID,
) -> ReportDraft:
    """The unsaved draft (version 0): one section per template section, in the template order."""
    by_section: dict[str, list[Activity]] = {s.key: [] for s in template.sections}
    for activity in eligible_activities(activities):
        target = group_target(group_map, activity)
        if target is not None and target.section_key in by_section:
            by_section[target.section_key].append(activity)
    sections = tuple(
        DraftSection(
            key=section.key,
            title=section.title,
            entries=tuple(
                _new_entry(a)
                for a in sorted(by_section[section.key], key=lambda a: _sort_key(section, a))
            ),
        )
        for section in template.sections
    )
    return ReportDraft(process_id, template.id, template.version, sections, version=0)


def _is_empty(section: DraftSection) -> bool:
    return not section.entries and not section.free_text.strip()


def empty_sections(draft: ReportDraft) -> tuple[str, ...]:
    """Keys of the sections with no entry and no typed text (REL-11)."""
    return tuple(s.key for s in draft.sections if _is_empty(s))


def document_sections(draft: ReportDraft) -> tuple[DraftSection, ...]:
    """The sections that go in the document: the empty ones are left out (REL-11)."""
    return tuple(s for s in draft.sections if not _is_empty(s))
