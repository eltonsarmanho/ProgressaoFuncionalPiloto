"""What a generated document reads from the process (TAB-01, TAB-02, UIG-06).

Everything is read in the unit of work the caller opened and comes back as plain tuples, so the
caller can close the unit and render without a database connection.

A document flagged outside the interstice creates no activity and is not part of any generated
document: its links and its pages are left out here, so the Tabela, the Relatório and the
Comprovante never carry it (FORA-01).

Only the valid activities go in (SEG-01): one outside the interstice, a duplicate, a rejected one
or one below the minimum hours is left out without a trace, not even as "Não pontuada". A valid
activity with no category cannot be placed in the table, so the generation is refused until the
person picks it (SEG-05).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.application.use_cases.scoring import ProcessScore, compute_process_score
from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.comprovante import ComprovanteLayout
from app.domain.entities.document import Document
from app.domain.entities.generated import GenerationCode
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.errors import GenerationRefused, NotFound
from app.domain.repositories.ports import ActivityEvidence, UnitOfWork
from app.domain.rules.activity_order import eligible_activities, table_order
from app.domain.rules.activity_validity import Validity
from app.domain.rules.comprovante_plan import current_layout, derive_layout
from app.domain.rules.interstice import Interstice
from app.domain.rules.table_document import TableHeader

# Reason a valid activity stays out of the documents, as the key of `GenerationInputs.excluded`.
PENDING = "pendentes"


@dataclass(frozen=True)
class GenerationInputs:
    """`activities` are the validated valid ones with group and item, in the order of the table;
    `excluded` counts the valid ones left out by reason. `evidences`, `documents` and `layout`
    leave out the documents flagged outside the interstice."""

    process: FunctionalProcess
    professor: Professor
    unit: AcademicUnit
    score: ProcessScore
    activities: tuple[Activity, ...]
    excluded: Mapping[str, int]
    evidences: tuple[ActivityEvidence, ...]
    documents: tuple[Document, ...]
    layout: ComprovanteLayout

    @property
    def version(self) -> ScoringTableVersion | None:
        return self.score.chosen.version if self.score.chosen is not None else None

    @property
    def interstice(self) -> Interstice:
        return Interstice(self.process.start_date, self.process.end_date)

    @property
    def header(self) -> TableHeader:
        return TableHeader(
            professor_name=self.professor.full_name,
            current_class=self.process.current_class,
            current_level=self.process.current_level,
            target_class=self.process.target_class,
            target_level=self.process.target_level,
            unit_name=self.unit.name,
            interstice=self.interstice,
        )


def _excluded(
    activities: Sequence[Activity], validity: Mapping[UUID, Validity]
) -> dict[str, int]:
    """The valid activities that do not go in, by reason; a reason with none is not listed.

    Only the ones awaiting validation: the not valid are no part of the process as far as the
    documents go, and one with no category refuses the generation.
    """
    pending = sum(
        1
        for activity in activities
        if validity[activity.id].is_valid and activity.status is ActivityStatus.AGUARDANDO_REVISAO
    )
    return {PENDING: pending} if pending else {}


def _without_documents(layout: ComprovanteLayout, ignored: set[UUID]) -> ComprovanteLayout:
    """The layout with the pages of the given documents taken out, as the user would have."""
    return replace(
        layout,
        activities=tuple(
            replace(entry, pages=tuple(p for p in entry.pages if p.document_id not in ignored))
            for entry in layout.activities
        ),
    )


def load_generation_inputs(uow: UnitOfWork, process: FunctionalProcess) -> GenerationInputs:
    """The process as the generation sees it now; the score is `compute_process_score` (AD-006)."""
    score = compute_process_score(uow, process)
    validity = score.result.validity
    # with no table chosen the request is refused for that reason first (TABELA_NAO_ESCOLHIDA)
    if score.chosen is not None and any(
        found.is_valid and found.needs_category for found in validity.values()
    ):
        raise GenerationRefused(
            GenerationCode.ATIVIDADE_SEM_CATEGORIA,
            "Há atividades sem categoria na Etapa 3. Escolha a categoria de cada uma.",
        )
    professor = uow.professors.get(process.professor_id)
    unit = uow.units.get(process.unit_id)
    if professor is None or unit is None:
        raise NotFound("Docente ou unidade do processo não encontrado")
    eligible = eligible_activities(score.activities, validity)
    activities = sorted(eligible, key=table_order)
    documents = uow.documents.list_for_process(process.id)
    ignored = {d.id for d in documents if d.outside_interstice}
    evidences = tuple(
        e
        for e in uow.evidences.list_for_activities([a.id for a in activities])
        if e.document_id not in ignored
    )
    saved = uow.comprovante_layouts.get(process.id)
    layout = (
        derive_layout(process.id, activities, evidences)
        if saved is None
        else current_layout(_without_documents(saved, ignored), activities, evidences)
    )
    return GenerationInputs(
        process=process,
        professor=professor,
        unit=unit,
        score=score,
        activities=tuple(activities),
        excluded=_excluded(score.activities, validity),
        evidences=evidences,
        documents=tuple(d for d in documents if d.id not in ignored),
        layout=layout,
    )
