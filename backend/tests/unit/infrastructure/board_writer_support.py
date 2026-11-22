"""A Parecer and a Requerimento document built from synthetic data, for the writer tests."""

from datetime import date
from decimal import Decimal

from app.domain.entities.board import OpinionConclusion
from app.domain.entities.generated import DocumentKind
from app.domain.rules.opinion_document import OpinionDocument, build_opinion
from app.domain.rules.request_document import RequestDocument, build_request
from app.domain.rules.scoring_verification import MinimumComparison, MinimumStatus
from tests.unit.domain.board_document_support import (
    PAGE,
    PROFESSOR,
    UNIT,
    opinion,
    ordinance,
    process,
)

GROUP_NAMES = {
    1: "Atividades de ensino",
    2: "Orientações",
    3: "Bancas",
    4: "Extensão",
    5: "Pesquisa",
    6: "Administração",
    7: "Capacitação",
    8: "Outras atividades",
}
SNAPSHOT = {
    "total": "211.00",
    "subtotals": {"1": "100.00", "2": "50.50", "4": "7.00", "5": "30.00"},
}
VERSIONS = {DocumentKind.TABELA: 3, DocumentKind.RELATORIO: 2, DocumentKind.COMPROVANTE: None}
MINIMUM = MinimumComparison(MinimumStatus.ATINGE, Decimal("200.00"), Decimal("211.00"))


def opinion_model(
    members=None,
    notes: str | None = "Sem observações adicionais.",
    conclusion=OpinionConclusion.FAVORAVEL,
) -> OpinionDocument:
    board = ordinance() if members is None else ordinance(members=members)
    return build_opinion(
        process(),
        PROFESSOR,
        UNIT,
        board,
        opinion(conclusion, notes=notes),
        SNAPSHOT,
        VERSIONS,
        MINIMUM,
        GROUP_NAMES,
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
