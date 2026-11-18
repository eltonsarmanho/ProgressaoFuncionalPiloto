"""What goes to the AI to word a report section, and what comes back to the draft (REL-03..07).

Only fields of the activity are sent, written like the template text and with the identifiers
masked; nothing of the pages, the author or the evidence note (AD-014).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.rules.masking import mask_identifiers
from app.domain.rules.report_draft import activity_fields

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
