"""Rascunho do Relatório: distribution of the activities by section and its order (REL-01, REL-02).

Pure functions. The group map is configuration: it says to which section an activity goes and,
for a section that gathers several groups, under which subtitle. The draft keeps entries in the
order of the section; the writers read subtitles, periods and modalities from the activities.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.domain.entities.activity import Activity, PeriodPrecision
from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.report import (
    DraftEntry,
    DraftSection,
    EntrySource,
    EntrySpec,
    GroupBy,
    MatchRule,
    ReportDraft,
    ReportTemplate,
    TemplateSection,
)
from app.domain.errors import NotFound
from app.domain.rules.activity_order import eligible_activities, table_order
from app.domain.rules.pt_format import format_date, format_decimal, format_hours, format_period
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


_COURSE = re.compile(
    r"\bcurso\s+(?:de|em|do|da)\s+(?P<name>[^,;.\n()]+)"
    r"|\b(?P<degree>(?:licenciatura|bacharelado|tecnologia)\s+em\s+[^,;.\n()]+)",
    re.IGNORECASE,
)


def _course(activity: Activity) -> str | None:
    """The course named in the title or in the description; the activity does not store it."""
    for text in (activity.title, activity.description):
        found = _COURSE.search(text)
        if found is not None:
            name = (found.group("name") or found.group("degree")).split(" - ")[0].strip()
            if name:
                return name
    return None


def _day(value, precision: PeriodPrecision) -> str:
    return value.strftime("%m/%Y") if precision is PeriodPrecision.MONTH else format_date(value)


def _dates(activity: Activity) -> str | None:
    precision = activity.period_precision
    if activity.event_date is not None:
        return _day(activity.event_date, precision)
    start, end = activity.period_start, activity.period_end
    if start is not None and end is not None:
        return f"{_day(start, precision)} a {_day(end, precision)}"
    if start is not None:
        return f"desde {_day(start, precision)}"
    if end is not None:
        return f"até {_day(end, precision)}"
    return None


def activity_fields(activity: Activity) -> dict[str, str]:
    """The markers an entry template can use, written in Portuguese; a marker without value is
    left out. Fields the activity does not have (funding source, collaborators, ordinance) are
    never here, so no template line can show them."""
    candidates = {
        "title": activity.title,
        "description": activity.description,
        "dates": _dates(activity),
        "period": format_period(activity.academic_period) if activity.academic_period else None,
        "hours": format_hours(activity.hours) if activity.hours is not None else None,
        "course_hours": (
            format_hours(activity.course_hours) if activity.course_hours is not None else None
        ),
        "quantity": format_decimal(activity.quantity) if activity.quantity is not None else None,
        "course": _course(activity),
    }
    return {name: value.strip() for name, value in candidates.items() if value and value.strip()}


_PIECE = re.compile(r"\[(?P<optional>[^\[\]]*)\]|\{(?P<marker>\w+)\}")
_MARKER = re.compile(r"\{(\w+)\}")


def _fill(text: str, values: Mapping[str, str]) -> tuple[str, bool]:
    """The text with each marker written; False when a marker had no value."""
    complete = True

    def write(found: re.Match[str]) -> str:
        nonlocal complete
        value = values.get(found.group(1))
        if value is None:
            complete = False
            return ""
        return value

    return _MARKER.sub(write, text), complete


def _render(template: str, values: Mapping[str, str]) -> tuple[str, bool]:
    """A template with markers; a `[...]` part is dropped when one of its markers has no value."""
    complete = True

    def write(found: re.Match[str]) -> str:
        nonlocal complete
        if found.group("optional") is not None:
            text, filled = _fill(found.group("optional"), values)
            return text if filled else ""
        text, filled = _fill(found.group(0), values)
        complete = complete and filled
        return text

    return _PIECE.sub(write, template), complete


def template_text(entry_spec: EntrySpec, activity: Activity) -> str:
    """The deterministic text of an entry (REL-12): the `line`, or one `Label: value` line per
    field whose markers all have a value. Nothing outside the fields of the activity is written."""
    values = activity_fields(activity)
    if entry_spec.line is not None:
        return _render(entry_spec.line, values)[0].strip()
    lines = []
    for label, template in entry_spec.fields:
        text, complete = _render(template, values)
        if complete and text.strip():
            lines.append(f"{label}: {text.strip()}")
    return "\n".join(lines)


def _new_entry(section: TemplateSection, activity: Activity) -> DraftEntry:
    return DraftEntry(activity.id, template_text(section.entry, activity), EntrySource.MODELO)


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
                _new_entry(section, a)
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


STALE = GenerationAlertCode.RASCUNHO_DESATUALIZADO
STALE_MESSAGE = "Há atividades novas ou removidas desde a última edição do Relatório."


def reconcile_draft(
    draft: ReportDraft,
    activities: Sequence[Activity],
    template: ReportTemplate,
    group_map: GroupMap,
) -> ReportDraft:
    """The saved draft brought up to date with the validated activities (REL-07, REL-08).

    An activity the draft does not know goes to the end of its section; an entry of an activity
    that is gone leaves; both make the section carry `RASCUNHO_DESATUALIZADO`. An entry stays in
    the section where it is, so a moved activity stays moved. The text of an entry from the
    template follows the activity; the text of the AI is kept and the text typed by the user is
    never touched.
    """
    current = {a.id: a for a in eligible_activities(activities)}
    known = {e.activity_id for s in draft.sections for e in s.entries}
    arrivals: dict[str, list[Activity]] = {s.key: [] for s in draft.sections}
    for activity in sorted((a for a in current.values() if a.id not in known), key=table_order):
        target = group_target(group_map, activity)
        if target is not None and target.section_key in arrivals:
            arrivals[target.section_key].append(activity)

    sections = []
    for section in draft.sections:
        spec = template.section(section.key)
        kept = []
        for entry in section.entries:
            activity = current.get(entry.activity_id)
            if activity is None:
                continue
            if entry.source is EntrySource.MODELO and spec is not None:
                entry = replace(entry, text=template_text(spec.entry, activity))
            kept.append(entry)
        added = [_new_entry(spec, a) for a in arrivals[section.key]] if spec is not None else []
        warnings = tuple(w for w in section.warnings if w.code is not STALE)
        if added or len(kept) != len(section.entries):
            warnings += (GenerationAlert(STALE, STALE_MESSAGE),)
        sections.append(replace(section, entries=(*kept, *added), warnings=warnings))
    return replace(draft, sections=tuple(sections))


def move_entry(
    draft: ReportDraft,
    activity_id: UUID,
    section_key: str,
    activities: Sequence[Activity],
    template: ReportTemplate,
) -> ReportDraft:
    """The draft with the activity at the end of the chosen section (REL-08).

    The text typed by the user goes with it; any other text is written again from the template
    of the new section.
    """
    entry = next(
        (e for s in draft.sections for e in s.entries if e.activity_id == activity_id), None
    )
    if entry is None:
        raise NotFound("Atividade não encontrada no rascunho")
    target = template.section(section_key)
    if target is None or all(s.key != section_key for s in draft.sections):
        raise NotFound("Seção não encontrada")
    if entry in next(s for s in draft.sections if s.key == section_key).entries:
        return draft
    if entry.source is not EntrySource.USUARIO:
        activity = next((a for a in activities if a.id == activity_id), None)
        if activity is None:
            raise NotFound("Atividade não encontrada")
        entry = _new_entry(target, activity)
    sections = tuple(
        replace(
            s,
            entries=(
                *(e for e in s.entries if e.activity_id != activity_id),
                *((entry,) if s.key == section_key else ()),
            ),
        )
        for s in draft.sections
    )
    return replace(draft, sections=sections)
