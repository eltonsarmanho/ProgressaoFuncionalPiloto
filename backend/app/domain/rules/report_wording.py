"""What goes to the AI to word a report section, and what comes back to the draft (REL-03..07).

Only fields of the activity are sent, written like the template text and with the identifiers
masked; nothing of the pages, the author or the evidence note (AD-014).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.report import DraftEntry, EntrySource, ReportDraft, ReportTemplate
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.errors import NotFound
from app.domain.rules.masking import mask_identifiers
from app.domain.rules.report_draft import activity_fields, template_text
from app.domain.rules.report_grounding import WordingReason, WordingVocabulary, check_wording

# Marker of the activity fields -> key of the payload sent to the AI.
_KEYS = {
    "title": "titulo",
    "dates": "datas",
    "hours": "carga_horaria",
    "course_hours": "carga_horaria_curso",
    "period": "periodo_letivo",
    "quantity": "quantidade",
    "description": "descricao",
}
_MASKED = ("title", "description")


@dataclass(frozen=True)
class WordingItem:
    """One activity as the AI sees it: an opaque id and the fields; `fields` are the facts the
    answer is checked against."""

    activity_id: UUID
    fields: dict[str, str]

    def payload(self) -> dict[str, str]:
        return {"id": str(self.activity_id), **self.fields}


def build_wording_items(
    activities: Sequence[Activity], version: ScoringTableVersion | None = None
) -> list[WordingItem]:
    """One item per activity; the type is the criterion of the table, when there is one."""
    items = []
    for activity in activities:
        values = activity_fields(activity)
        fields: dict[str, str] = {}
        criterion = None
        if version is not None and activity.group_number and activity.item_number:
            criterion = version.get_criterion(activity.group_number, activity.item_number)
        if criterion is not None:
            fields["tipo"] = criterion.description
        for marker, key in _KEYS.items():
            if marker in values:
                text = values[marker]
                fields[key] = mask_identifiers(text).text if marker in _MASKED else text
        items.append(WordingItem(activity.id, fields))
    return items


_WORDING_CODES = (GenerationAlertCode.REDACAO_REJEITADA, GenerationAlertCode.REDACAO_INDISPONIVEL)


@dataclass(frozen=True)
class WordingApplied:
    """The draft after the wording and the warnings the section got (the job keeps them too)."""

    draft: ReportDraft
    warnings: tuple[GenerationAlert, ...]


def activities_to_word(
    draft: ReportDraft, section_key: str, activities: Sequence[Activity]
) -> list[Activity]:
    """The activities of the section whose entry the user did not write: only they are sent."""
    by_id = {a.id: a for a in activities}
    section = next((s for s in draft.sections if s.key == section_key), None)
    if section is None:
        raise NotFound("Seção não encontrada")
    return [
        by_id[e.activity_id]
        for e in section.entries
        if e.source is not EntrySource.USUARIO and e.activity_id in by_id
    ]


def apply_wording(
    draft: ReportDraft,
    section_key: str,
    results: Mapping[UUID, str] | None,
    *,
    template: ReportTemplate,
    activities: Sequence[Activity],
    items: Sequence[WordingItem],
    vocabulary: WordingVocabulary,
) -> WordingApplied:
    """Apply the answer of the AI to the entries of one section (REL-04, REL-05, REL-07).

    `results` is None when the AI was unavailable: every entry the user did not write gets the
    template text and the section `REDACAO_INDISPONIVEL`. Otherwise each answer stays as source
    IA only when it passes the check against the fields sent; a refused one gives the template
    text and `REDACAO_REJEITADA` with the reasons. An entry without answer, with a blank answer or
    whose activity was not sent stays as it was; the text of the user is never touched. The
    version of the draft does not change.
    """
    section = next((s for s in draft.sections if s.key == section_key), None)
    spec = template.section(section_key)
    if section is None or spec is None:
        raise NotFound("Seção não encontrada")
    by_id = {a.id: a for a in activities}
    facts = {item.activity_id: item.fields for item in items}
    rejected: set[str] = set()

    def reword(entry: DraftEntry) -> DraftEntry:
        activity = by_id.get(entry.activity_id)
        if entry.source is EntrySource.USUARIO or activity is None:
            return entry
        model = template_text(spec.entry, activity)
        if results is None:
            return DraftEntry(entry.activity_id, model, EntrySource.MODELO)
        answer = (results.get(entry.activity_id) or "").strip()
        if not answer or entry.activity_id not in facts:
            return entry
        check = check_wording(answer, facts[entry.activity_id], vocabulary, model)
        if check.accepted:
            return DraftEntry(entry.activity_id, check.text, EntrySource.IA)
        reasons = ",".join(r.value for r in check.reasons)
        rejected.update(r.value for r in check.reasons)
        warning = GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, reasons)
        return DraftEntry(entry.activity_id, model, EntrySource.MODELO, (warning,))

    entries = tuple(reword(e) for e in section.entries)
    warnings: tuple[GenerationAlert, ...] = ()
    if results is None:
        warnings = (GenerationAlert(GenerationAlertCode.REDACAO_INDISPONIVEL),)
    elif rejected:
        reasons = ",".join(r for r in WordingReason if r.value in rejected)
        warnings = (GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, reasons),)
    kept = tuple(w for w in section.warnings if w.code not in _WORDING_CODES)
    changed = replace(section, entries=entries, warnings=(*kept, *warnings))
    sections = tuple(changed if s.key == section_key else s for s in draft.sections)
    return WordingApplied(replace(draft, sections=sections), warnings)
