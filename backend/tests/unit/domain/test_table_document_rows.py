"""TAB-02, TAB-03: header, group bands and rows of the scoring table document."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.activity import Level
from app.domain.rules.table_document import MAX_TITLE_CHARS, TableHeader, build_table_document
from tests.unit.domain.scenario_211 import (
    INTERSTICE,
    activity,
    official_like_table,
    scenario_303_result,
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
    # SEG-01: two same-title activities are one when they are duplicates; two rows only when
    # the second is marked as distinct
    one = activity(3, 2, title="Banca de TCC")
    two = activity(
        3, 2, title="Banca de TCC", distinct_justification="Outra banca",
        created_at=datetime(2025, 1, 2, tzinfo=UTC),
    )  # fmt: skip

    document = build(activities=[one, two])

    assert len(document.bands[1].rows) == 2


def test_a_duplicate_of_another_activity_has_no_row():
    # SEG-01
    one = activity(3, 2, title="Banca de TCC")
    two = activity(3, 2, title="Banca de TCC", created_at=datetime(2025, 1, 2, tzinfo=UTC))

    document = build(activities=[one, two])

    assert [r.activity_id for r in document.bands[1].rows] == [one.id]


def test_an_activity_that_does_not_score_keeps_its_row_with_zero_points_and_its_status():
    # SEG-01: outside the interstice has no row; the activity that does not score is the one
    # whose item the table does not have
    unlisted = activity(2, 99, title="Item fora da tabela")

    document = build(activities=[unlisted])
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


# --- group I as section I of the table (GTAB-01, GTAB-02, GTAB-03, GTAB-05, GTAB-07) ------------


def offer(title, period, hours="68", level=Level.GRADUACAO, item=1, **kwargs):
    return activity(
        1, item, hours=Decimal(hours), level=level, academic_period=period, title=title, **kwargs
    )


def build_inside(activities=None):
    version, activities, result = scenario_303_result(activities)
    return build_table_document(HEADER, version, result, activities, NO_NUMBERS)


def section_one(activities=None):
    return build_inside(activities).bands[0]


def test_the_new_version_opens_with_the_band_of_group_one_and_its_subtotal():
    # GTAB-01
    document = build_inside()

    band = document.bands[0]
    assert (band.group_number, band.numeral, band.name, band.subtotal) == (
        1, "I", "Docência", "92,00",
    )  # fmt: skip
    assert [b.group_number for b in document.bands] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_the_scenario_303_total_is_the_sum_of_groups_i_to_viii():
    # GTAB-03
    document = build_inside()

    assert document.total == "303,00"


def test_each_group_one_offer_is_a_row_with_item_title_period_hours_unit_and_total():
    # GTAB-02
    cálculo = offer("Cálculo I", "2023.1")
    pos = offer("Métodos", "2023.2", hours="68", level=Level.POS_GRADUACAO, item=2)

    band = section_one([cálculo, pos])

    assert [
        (r.item, r.title, r.quantity, r.unit_points, r.points) for r in band.rows
    ] == [
        ("I.1", "Cálculo I (1º Período de 2023)", "8,00", "1,00", "8,00"),
        ("I.2", "Métodos (2º Período de 2023)", "12,00", "1,00", "12,00"),
    ]
    assert band.subtotal == "20,00"


def test_the_offers_are_ordered_by_term_and_then_by_title_ignoring_case():
    # GTAB-02: 2022.2 before 2023.1 whatever the title; "álgebra" before "Banco" in one term
    late = offer("Aaa disciplina", "2023.1")
    banco = offer("Banco de dados", "2023.1")
    algebra = offer("álgebra linear", "2023.1")
    early = offer("Zzz disciplina", "2022.2")

    band = section_one([late, banco, algebra, early])

    assert [r.title for r in band.rows] == [
        "Zzz disciplina (2º Período de 2022)",
        "Aaa disciplina (1º Período de 2023)",
        "álgebra linear (1º Período de 2023)",
        "Banco de dados (1º Período de 2023)",
    ]


def test_an_offer_without_a_term_comes_last_and_has_only_its_title():
    # GTAB-02
    no_term = offer("Aaa sem período", None)
    termed = offer("Zzz com período", "2023.2")

    band = section_one([no_term, termed])

    assert [r.title for r in band.rows] == [
        "Zzz com período (2º Período de 2023)",
        "Aaa sem período",
    ]


def test_a_title_of_401_characters_is_cut_at_400_with_an_ellipsis_and_the_term_comes_after():
    # edge case: the same cut as the other rows
    long = offer("b" * (MAX_TITLE_CHARS + 1), "2023.1")

    band = section_one([long])

    assert band.rows[0].title == "b" * (MAX_TITLE_CHARS - 1) + "…" + " (1º Período de 2023)"


def test_every_group_one_row_scores_its_hours_so_the_constant_unit_of_one_cannot_lie():
    # D7: points == hours, unit 1,00
    band = section_one()

    assert len(band.rows) == 12
    assert {r.unit_points for r in band.rows} == {"1,00"}
    assert all(r.points == r.quantity for r in band.rows)


def test_a_group_one_row_that_scores_nothing_keeps_zero_points_and_its_reason_in_the_alerts():
    # GTAB-05
    unlisted = offer("Disciplina sem item", "2023.1", item=99)
    version, activities, result = scenario_303_result([unlisted])

    document = build_table_document(HEADER, version, result, activities, NO_NUMBERS)
    row = document.bands[0].rows[0]

    assert (row.item, row.points) == ("I.99", "0,00")
    assert [(a.code, a.subject) for a in document.alerts] == [
        ("SEM_ENQUADRAMENTO", "Disciplina sem item")
    ]


def test_a_term_with_only_offers_outside_the_interstice_has_no_row():
    # edge case: GI-04 and GI-09, the whole year of 2019 is outside
    old = [
        offer("Disciplina antiga", "2019.1", event_date=None),
        offer("Outra antiga", "2019.1", event_date=None),
    ]
    inside = offer("Disciplina atual", "2023.1", event_date=None)

    band = section_one([*old, inside])

    assert [r.title for r in band.rows] == ["Disciplina atual (1º Período de 2023)"]
    assert band.subtotal == "8,00"


def test_the_old_version_has_no_section_i_and_marks_the_hours_as_outside_the_total():
    # GTAB-07
    document = build()

    assert 1 not in [b.group_number for b in document.bands]
    assert document.pit_hours.outside_total is True
    assert document.total == "211,00"


def test_the_new_version_hours_section_is_not_marked_as_outside_the_total():
    # GTAB-06, GTAB-07
    document = build_inside()

    assert document.pit_hours.outside_total is False
    assert document.pit_hours.total == "92,00"

