"""The scoring table document of the acceptance scenario and a very long one, for the writers."""

from dataclasses import replace
from uuid import uuid4

from app.domain.rules.scoring_engine import Counters
from app.domain.rules.table_document import TableDocument, TableRow, build_table_document
from tests.unit.domain.scenario_211 import (
    INTERSTICE,
    activity,
    item_capped_table,
    scenario_303_result,
    scenario_result,
)
from tests.unit.domain.test_table_document_totals import HEADER

SUBTOTALS = {"II": "52,00", "III": "7,00", "IV": "62,00", "V": "0,00", "VI": "30,00",
             "VII": "4,00", "VIII": "56,00"}  # fmt: skip
PIT_HOURS = ["24,00", "24,00", "24,00", "20,00"]
INTERSTICE_TEXT = "23/11/2022 a 23/11/2024"
assert INTERSTICE.start.year == 2022


def scenario_table(header=HEADER) -> TableDocument:
    version, activities, result = scenario_result()
    return build_table_document(header, version, result, activities)


def scenario_303_table() -> TableDocument:
    """The scenario with group I inside the total: section I, 303 points, hours in the total."""
    version, activities, result = scenario_303_result()
    return build_table_document(HEADER, version, result, activities)


def long_table(rows: int = 1000, title: str = "Atividade sintética") -> TableDocument:
    """The scenario document with `rows` rows in its first band."""
    document = scenario_table()
    band = document.bands[0]
    many = tuple(
        TableRow(uuid4(), "II.3", f"{title} {n}", "1,00", "20,00", "20,00")
        for n in range(rows)
    )
    return replace(document, bands=(replace(band, rows=many), *document.bands[1:]))


def capped_table() -> TableDocument:
    """Ten orientations at item 7 of group II, limited to 40 points: rows say 160, the subtotal and
    the total say 40."""
    ten = [activity(2, 7, "10", title="Muitas orientações")]
    version, activities, result = scenario_result(ten, item_capped_table())
    return build_table_document(HEADER, version, result, activities)


def distinct_counters_table() -> TableDocument:
    """The scenario with five different counters, so a wrong label shows."""
    return replace(scenario_table(), counters=Counters(21, 17, 5, 3, 2))


def table_with_title(title: str) -> TableDocument:
    """The document built, as in production, from one activity with the given title."""
    one = [activity(2, 7, "1", title=title)]
    version, activities, result = scenario_result(one)
    return build_table_document(HEADER, version, result, activities)


BIG_SUBTOTAL = "1.234.567,00"


def wide_band_table() -> TableDocument:
    """A row with a title cut at 400 characters under a band whose subtotal has seven digits."""
    title = " ".join(f"palavra{n}" for n in range(1000))
    document = table_with_title(title)
    band = replace(document.bands[0], subtotal=BIG_SUBTOTAL)
    return replace(document, bands=(band, *document.bands[1:]), total=BIG_SUBTOTAL)


NEW_PIT_HEADING = "Horas de PIT por semestre (Grupo I)"
OLD_PIT_HEADING = "Horas de PIT por semestre (Grupo I, fora do total de pontos)"
