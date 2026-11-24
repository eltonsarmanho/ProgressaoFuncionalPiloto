"""A Parecer and a Requerimento document built from synthetic data, for the writer tests."""

from datetime import date

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.board import OpinionConclusion
from app.domain.rules.opinion_document import OpinionDocument, build_opinion
from app.domain.rules.request_document import RequestDocument, build_request
from tests.unit.domain.board_document_support import (
    CAMPUS,
    PAGE,
    PROFESSOR,
    UNIT,
    opinion,
    ordinance,
    process,
)


def opinion_model(
    members=None,
    conclusion=OpinionConclusion.FAVORAVEL,
    parent_unit: AcademicUnit | None = CAMPUS,
    **opinion_changes,
) -> OpinionDocument:
    board = ordinance() if members is None else ordinance(members=members)
    return build_opinion(
        process(),
        PROFESSOR,
        UNIT,
        parent_unit,
        board,
        opinion(conclusion, **opinion_changes),
        PAGE,
    )


def request_model(
    city: str | None = "Belém",
    last_opinion: date | None = None,
    professor=PROFESSOR,
) -> RequestDocument:
    return build_request(
        process(), professor, UNIT, "MAGISTERIO_SUPERIOR", city, last_opinion, PAGE
    )
