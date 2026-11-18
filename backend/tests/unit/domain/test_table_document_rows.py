"""TAB-02, TAB-03: header, group bands and rows of the scoring table document."""

from dataclasses import replace
from decimal import Decimal

from app.domain.rules.table_document import MAX_TITLE_CHARS, TableHeader, build_table_document
from tests.unit.domain.scenario_211 import (
    INTERSTICE,
    activity,
    official_like_table,
    scenario_result,
)

HEADER = TableHeader(
    professor_name="Maria Docente da Silva",
    current_class="Adjunto",
    current_level=2,
    target_class="Associado",
    target_level=1,
    unit_name="Faculdade de Testes",
    interstice=INTERSTICE,
)
NO_NUMBERS: dict = {}


def build(activities=None, version=None, numbers=None, header=HEADER):
    version, activities, result = scenario_result(activities, version)
    return build_table_document(header, version, result, activities, numbers or NO_NUMBERS)


def test_the_header_names_the_professor_the_classes_the_unit_and_the_interstice():
    document = build()

    assert document.header == HEADER


def test_the_header_names_the_table_version_and_its_normative_reference():
    document = build()

    assert document.table_name == "Tabela de teste 2022"
    assert document.norm_reference == "Res. de teste, Anexo I"


def test_the_211_scenario_has_seven_bands_with_the_group_subtotals():
    document = build()

    assert [b.group_number for b in document.bands] == [2, 3, 4, 5, 6, 7, 8]
    assert [b.subtotal for b in document.bands] == [
        "52,00", "7,00", "62,00", "0,00", "30,00", "4,00", "56,00",
    ]  # fmt: skip


def test_a_band_carries_the_roman_numeral_and_the_name_of_the_table_group():
    document = build()

    assert [(b.numeral, b.name) for b in document.bands[:2]] == [
        ("II", "Orientação"),
        ("III", "Bancas"),
    ]
    assert (document.bands[-1].numeral, document.bands[-1].name) == ("VIII", "Produção")


def test_a_group_without_activity_is_a_band_with_zero_and_no_row():
    document = build()

    empty = next(b for b in document.bands if b.group_number == 5)

    assert (empty.rows, empty.subtotal) == ((), "0,00")


def test_group_one_outside_the_total_has_no_band():
    document = build()

    assert 1 not in [b.group_number for b in document.bands]


def test_group_one_counting_in_the_total_is_a_band_like_the_others():
    version = official_like_table()
    first = replace(version.groups[0], counts_in_total=True)
    counting = replace(version, groups=(first, *version.groups[1:]))

    document = build(activities=[], version=counting)

    assert [b.group_number for b in document.bands] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert document.bands[0].subtotal == "0,00"


def test_the_columns_of_a_row_are_item_title_quantity_unit_total_voucher_and_status():
    a = activity(2, 7, "2", title="Orientação de TCC")
    version, activities, result = scenario_result([a])

    document = build_table_document(HEADER, version, result, activities, {a.id: 14})
    row = document.bands[0].rows[0]

    assert (row.item, row.title, row.quantity, row.unit_points, row.points) == (
        "II.7", "Orientação de TCC", "2,00", "16,00", "32,00",
    )  # fmt: skip
    assert (row.comprovante, row.status) == ("14", "Pontuada")


def test_a_row_without_a_voucher_number_reads_sem_comprovante():
    a = activity(3, 2)

    document = build(activities=[a])

    assert document.bands[1].rows[0].comprovante == "sem comprovante"


def test_a_row_takes_its_voucher_number_from_the_plan_by_activity():
    first, second = activity(3, 2), activity(3, 2)

    document = build(activities=[first, second], numbers={second.id: 9})

    assert [r.comprovante for r in document.bands[1].rows] == ["sem comprovante", "9"]


def test_rows_follow_the_items_of_the_group_and_keep_the_order_inside_an_item():
    early = activity(2, 7, title="Segunda orientação")
    late = activity(2, 3, title="Primeira orientação")
    again = activity(2, 7, title="Terceira orientação")

    document = build(activities=[early, late, again])

    assert [(r.item, r.title) for r in document.bands[0].rows] == [
        ("II.3", "Primeira orientação"),
        ("II.7", "Segunda orientação"),
        ("II.7", "Terceira orientação"),
    ]


def test_two_activities_with_the_same_title_in_one_item_are_two_rows():
    one, two = activity(3, 2, title="Banca de TCC"), activity(3, 2, title="Banca de TCC")

    document = build(activities=[one, two])

    assert len(document.bands[1].rows) == 2


def test_an_activity_that_does_not_score_keeps_its_row_with_zero_points_and_its_status():
    late = activity(2, 7, title="Fora do prazo", event_date=INTERSTICE.start.replace(year=2019))

    document = build(activities=[late])
    row = document.bands[0].rows[0]

    assert (row.points, row.unit_points, row.quantity, row.status) == (
        "0,00", "—", "—", "Não pontuada",
    )  # fmt: skip


def test_an_activity_outside_the_given_list_has_no_row():
    listed = activity(3, 2, title="Na lista")
    version, activities, result = scenario_result([listed, activity(3, 2, title="Fora da lista")])

    document = build_table_document(HEADER, version, result, [listed], NO_NUMBERS)

    assert [r.title for r in document.bands[1].rows] == ["Na lista"]


def test_the_group_one_offers_are_not_rows_of_the_bands():
    document = build()

    assert sum(len(b.rows) for b in document.bands) == 8


def test_the_band_subtotal_is_the_one_of_the_engine_even_when_a_limit_cuts_the_rows():
    a = activity(2, 7, "10", title="Muitas orientações")
    capped = official_like_table()
    group_two = replace(
        capped.groups[1],
        criteria=(
            capped.groups[1].criteria[0],
            replace(capped.groups[1].criteria[1], max_points=Decimal("40")),
        ),
    )
    limited = replace(capped, groups=(capped.groups[0], group_two, *capped.groups[2:]))

    document = build(activities=[a], version=limited)

    assert document.bands[0].rows[0].points == "160,00"
    assert document.bands[0].subtotal == "40,00"


def shown_title(title: str) -> str:
    return build(activities=[activity(2, 7, title=title)]).bands[0].rows[0].title


def test_a_title_up_to_the_cap_is_shown_whole_and_a_longer_one_is_cut_with_an_ellipsis():
    exact = "a" * MAX_TITLE_CHARS
    over = "b" * (MAX_TITLE_CHARS + 1)

    assert shown_title(exact) == exact
    assert shown_title("c" * (MAX_TITLE_CHARS - 1)) == "c" * (MAX_TITLE_CHARS - 1)
    assert shown_title(over) == "b" * (MAX_TITLE_CHARS - 1) + "…"
    assert len(shown_title(over)) == MAX_TITLE_CHARS


def test_a_cut_title_is_the_same_every_time_and_as_long_as_the_cap():
    long_title = "palavra " * 200

    assert shown_title(long_title) == shown_title(long_title)
    assert len(shown_title(long_title)) == MAX_TITLE_CHARS
