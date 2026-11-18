"""The scoring table document of the acceptance scenario and a very long one, for the writers."""

from dataclasses import replace
from uuid import uuid4

from app.domain.rules.scoring_engine import Counters
from app.domain.rules.table_document import TableDocument, TableRow, build_table_document
from tests.unit.domain.scenario_211 import INTERSTICE, activity, item_capped_table, scenario_result
from tests.unit.domain.test_table_document_totals import HEADER

SUBTOTALS = {"II": "52,00", "III": "7,00", "IV": "62,00", "V": "0,00", "VI": "30,00",
             "VII": "4,00", "VIII": "56,00"}  # fmt: skip
PIT_HOURS = ["24,00", "24,00", "24,00", "20,00"]
INTERSTICE_TEXT = "23/11/2022 a 23/11/2024"
assert INTERSTICE.start.year == 2022


def scenario_table(header=HEADER) -> TableDocument:
    version, activities, result = scenario_result()
    return build_table_document(header, version, result, activities, {})


def long_table(rows: int = 1000, title: str = "Atividade sintética") -> TableDocument:
    """The scenario document with `rows` rows in its first band."""
    document = scenario_table()
    band = document.bands[0]
    many = tuple(
        TableRow(uuid4(), "II.3", f"{title} {n}", "1,00", "20,00", "20,00", str(n), "Pontuada")
        for n in range(rows)
    )
    return replace(document, bands=(replace(band, rows=many), *document.bands[1:]))


def capped_table() -> TableDocument:
    """Ten orientations at item 7 of group II, limited to 40 points: rows say 160, the subtotal and
    the total say 40."""
    ten = [activity(2, 7, "10", title="Muitas orientações")]
    version, activities, result = scenario_result(ten, item_capped_table())
    return build_table_document(HEADER, version, result, activities, {})


def distinct_counters_table() -> TableDocument:
    """The scenario with five different counters, so a wrong label shows."""
    return replace(scenario_table(), counters=Counters(21, 17, 5, 3, 2))
