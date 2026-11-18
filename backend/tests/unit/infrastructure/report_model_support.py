"""A report document built from the packaged template with synthetic activities."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.report import ReportDocument
from app.domain.rules.report_document import build_report_document
from app.domain.rules.report_draft import propose_draft
from app.infrastructure.documents.config_loader import load_report_config
from tests.unit.domain.scenario_211 import activity
from tests.unit.domain.test_table_document_totals import HEADER

NAMES = {(2, 3): "Orientação de dissertação de mestrado", (2, 7): "Orientação de graduação"}


def synthetic_activities(extra=()):
    graduation = {"academic_period": "2023.1", "course_hours": Decimal("60")}
    return [
        activity(1, 1, title="Cálculo Diferencial", **graduation),
        activity(1, 1, title="Álgebra Linear", **{**graduation, "academic_period": "2023.2"}),
        activity(2, 3, title="Dissertação de Maria Souza"),
        activity(5, 1, title="Projeto de pesquisa em Ação Educativa"),
        activity(
            4,
            4,
            title="Oficina de extensão",
            description="Oficina aberta à comunidade.",
            event_date=None,
            period_start=date(2023, 3, 1),
            period_end=date(2023, 6, 30),
        ),  # fmt: skip
        activity(7, 1, title="Curso de capacitação em ensino"),
        *extra,
    ]


def report_document(activities=None, header=HEADER) -> ReportDocument:
    config = load_report_config()
    activities = synthetic_activities() if activities is None else activities
    draft = propose_draft(config.template, activities, config.group_map, process_id=uuid4())
    return build_report_document(config, header, draft, activities, item_names=NAMES)
