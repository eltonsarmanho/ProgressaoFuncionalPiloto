"""TAB-01, TAB-03 to TAB-06: the scoring table written as PDF with reportlab."""

import re
from dataclasses import replace

import pymupdf

from app.domain.rules.table_document import TableAlert
from app.infrastructure.documents.table_pdf import write_table_pdf
from tests.unit.domain.test_table_document_totals import HEADER
from tests.unit.infrastructure.table_support import (
    BIG_SUBTOTAL,
    INTERSTICE_TEXT,
    PIT_HOURS,
    SUBTOTALS,
    capped_table,
    distinct_counters_table,
    long_table,
    scenario_table,
    table_with_title,
    wide_band_table,
)

COLUMNS = ["Item", "Atividade", "Quantidade", "Pontuação unitária", "Total"]
REMOVED_WORDS = (
    "Pontuada", "Potencial", "Não pontuada", "sem comprovante", "Comprovante", "Status",
)  # fmt: skip


def render(tmp_path, document) -> pymupdf.Document:
    target = tmp_path / "tabela.pdf"
    write_table_pdf(document, target)
    return pymupdf.open(target)


def text_of(pdf: pymupdf.Document) -> str:
    return " ".join(" ".join(page.get_text().split()) for page in pdf)


def test_the_211_scenario_has_the_total_the_subtotals_and_the_pit_hours(tmp_path):
    text = text_of(render(tmp_path, scenario_table()))

    assert "Pontuação geral: 211,00" in text
    for numeral, subtotal in SUBTOTALS.items():
        assert re.search(rf"\b{numeral}\. [^:]*?Subtotal: {re.escape(subtotal)}", text), numeral
    pit = text[text.index("Horas de PIT") :]
    assert re.findall(r"\b\d\d,00\b", pit.split("Alertas")[0]) == [*PIT_HOURS, "92,00"]


def test_the_table_has_the_five_columns_in_the_order_of_the_spec(tmp_path):
    pdf = render(tmp_path, scenario_table())

    tables = pdf[0].find_tables()
    assert tables.tables
    names = [name.replace("\n", " ") for name in tables.tables[0].header.names]
    assert names == COLUMNS


def test_the_page_is_a4_landscape(tmp_path):
    rect = render(tmp_path, scenario_table())[0].rect
    assert (round(rect.width), round(rect.height)) == (842, 595)


def test_the_header_names_the_professor_the_classes_the_unit_the_interstice_and_the_table(
    tmp_path,
):
    text = text_of(render(tmp_path, scenario_table()))

    assert "Docente: Maria Docente da Silva" in text
    assert "Classe e nível atuais: Adjunto, nível 2" in text
    assert "Classe e nível pretendidos: Associado, nível 1" in text
    assert "Unidade: Faculdade de Testes" in text
    assert f"Interstício: {INTERSTICE_TEXT}" in text
    assert "Tabela de pontuação: Tabela de teste 2022" in text
    assert "Referência normativa: Res. de teste, Anexo I" in text


def test_each_activity_is_a_row_with_item_quantity_and_points(tmp_path):
    text = text_of(render(tmp_path, scenario_table()))

    assert "II.3" in text
    assert "II.7" in text
    assert "20,00" in text


def test_no_cell_says_voucher_or_status_and_the_footer_has_no_voucher_nor_status_counters(
    tmp_path,
):
    # GTAB-04, GTAB-08
    pdf = render(tmp_path, scenario_table())
    cells = " ".join(
        " ".join(cell or "" for row in table.extract() for cell in row)
        for page in pdf
        for table in page.find_tables().tables
    )
    footer = next(
        line for line in text_of(pdf).split("Pontuação geral:")[1:] if "Atividades:" in line
    )

    for word in REMOVED_WORDS:
        assert word not in cells, word
    for word in ("Com comprovante", "Pendentes", "Não pontuadas"):
        assert word not in footer, word
    assert "Com divergências:" in footer


def test_a_title_of_400_characters_and_a_seven_digit_subtotal_keep_the_band_on_one_line(tmp_path):
    # GTAB-04
    pdf = render(tmp_path, wide_band_table())

    assert len(pdf[0].search_for(f"Subtotal: {BIG_SUBTOTAL}")) == 1
    assert len(pdf[0].search_for(f"Pontuação geral: {BIG_SUBTOTAL}")) == 1
    assert "palavra0 palavra1" in text_of(pdf)


def test_a_group_without_activity_still_has_its_band_with_zero(tmp_path):
    text = text_of(render(tmp_path, scenario_table()))

    assert re.search(r"V\. Pesquisa Subtotal: 0,00", text)


def test_the_counters_are_written_as_the_engine_counted_them(tmp_path):
    document = scenario_table()
    c = document.counters
    text = text_of(render(tmp_path, document))

    assert f"Atividades: {c.activities}" in text
    assert f"Com divergências: {c.with_alerts}" in text


def test_the_total_and_the_subtotal_are_the_limited_ones_not_the_sum_of_the_rows(tmp_path):
    text = text_of(render(tmp_path, capped_table()))

    assert "160,00" in text  # the row of the ten orientations
    assert "Pontuação geral: 40,00" in text
    assert re.search(r"II\. [^:]*?Subtotal: 40,00", text)
    assert "Pontuação geral: 160,00" not in text


def test_each_counter_is_written_under_its_own_label(tmp_path):
    text = text_of(render(tmp_path, distinct_counters_table()))

    assert "Atividades: 21" in text
    assert "Com divergências: 2" in text


def test_the_pit_section_is_left_out_when_the_table_does_not_measure_hours(tmp_path):
    text = text_of(render(tmp_path, replace(scenario_table(), pit_hours=None)))

    assert "Horas de PIT" not in text


def test_the_alerts_are_listed_with_the_words_of_the_screen_and_the_activity(tmp_path):
    alerts = (
        TableAlert("LIMITE_GRUPO", "Limite do grupo aplicado."),
        TableAlert("DATA_FIM_AUSENTE", "Data final ausente.", "Portaria de Diretor"),
    )
    text = text_of(render(tmp_path, replace(scenario_table(), alerts=alerts)))

    assert "Alertas" in text
    assert "Limite do grupo aplicado." in text
    assert "Portaria de Diretor: Data final ausente." in text


def test_no_alerts_heading_without_alerts(tmp_path):
    assert "Alertas" not in text_of(render(tmp_path, replace(scenario_table(), alerts=())))


def test_the_header_row_repeats_on_every_page_of_a_thousand_rows(tmp_path):
    pdf = render(tmp_path, long_table(1000))

    assert len(pdf) > 10
    for page in pdf:
        header = page.find_tables().tables[0].header.names
        assert [name.replace("\n", " ") for name in header] == COLUMNS


def test_the_footer_numbers_every_page_as_page_n_of_m(tmp_path):
    pdf = render(tmp_path, long_table(300))

    total = len(pdf)
    assert total > 1
    for index, page in enumerate(pdf, start=1):
        assert f"Página {index} de {total}" in " ".join(page.get_text().split())


def test_accents_and_markup_characters_in_names_and_titles_come_out_as_written(tmp_path):
    header = replace(HEADER, professor_name="Zoë Ñandú da Ação", unit_name="Faculdade ª ü ç")
    document = replace(scenario_table(header), bands=long_table(1).bands)
    document = replace(
        document,
        bands=(
            replace(
                document.bands[0],
                rows=(replace(document.bands[0].rows[0], title="Cálculo & Álgebra <I> ç"),),
            ),
            *document.bands[1:],
        ),
    )

    text = text_of(render(tmp_path, document))

    assert "Docente: Zoë Ñandú da Ação" in text
    assert "Unidade: Faculdade ª ü ç" in text
    assert "Cálculo & Álgebra <I> ç" in text


def test_the_font_is_liberation_serif_embedded_as_a_subset(tmp_path):
    pdf = render(tmp_path, long_table(2))

    names = {font[3].split("+")[-1] for font in pdf[0].get_fonts()}
    assert names == {"LiberationSerif", "LiberationSerif-Bold"}
    assert all(font[3].count("+") == 1 for font in pdf[0].get_fonts())


def test_a_title_of_eight_thousand_characters_does_not_break_the_pdf(tmp_path):
    # TAB-01: the title of an activity has no size limit in the schema; the Tabela cuts it
    title = " ".join(f"palavra{n}" for n in range(1000))  # about 8 000 characters
    assert len(title) > 7_000

    text = text_of(render(tmp_path, table_with_title(title)))

    assert "palavra0 palavra1" in text
    assert "palavra999" not in text
    assert "…" in text
    assert "Pontuação geral:" in text
