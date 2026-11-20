"""TAB-01, TAB-03 to TAB-06: the scoring table written as DOCX with python-docx."""

import re
import zipfile
from dataclasses import replace

from docx import Document
from docx.table import Table
from lxml import etree

from app.domain.rules.table_document import TableAlert
from app.infrastructure.documents.table_docx import write_table_docx
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

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
COLUMNS = ["Item", "Atividade", "Quantidade", "Pontuação unitária", "Total"]
REMOVED_WORDS = (
    "Pontuada", "Potencial", "Não pontuada", "sem comprovante", "Comprovante", "Status",
)  # fmt: skip


def write(tmp_path, document):
    target = tmp_path / "tabela.docx"
    write_table_docx(document, target)
    return target


def xml_of(path, part="word/document.xml"):
    with zipfile.ZipFile(path) as archive:
        return etree.fromstring(archive.read(part))


def text_of(path) -> str:
    """The body in order (paragraphs and table cells) and then the footer, read back."""
    document = Document(str(path))
    pieces = []
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                seen = []
                for cell in row.cells:
                    if cell._tc not in seen:  # a merged cell is listed once per column it covers
                        seen.append(cell._tc)
                        pieces.append(cell.text)
        else:
            pieces.append(block.text)
    for section in document.sections:
        pieces += [p.text for p in section.footer.paragraphs]
    return " ".join(" ".join(pieces).split())


def main_table(path):
    return xml_of(path).findall(".//w:tbl", NS)[0]


def test_the_211_scenario_has_the_total_the_subtotals_and_the_pit_hours(tmp_path):
    text = text_of(write(tmp_path, scenario_table()))

    assert "Pontuação geral: 211,00" in text
    for numeral, subtotal in SUBTOTALS.items():
        assert re.search(rf"\b{numeral}\. [^:]*?Subtotal: {re.escape(subtotal)}", text), numeral
    pit = text[text.index("Horas de PIT") :]
    assert re.findall(r"\b\d\d,00\b", pit) == [*PIT_HOURS, "92,00"]


def cell_texts(path) -> list[str]:
    """Every cell of the main table, a merged one once."""
    return ["".join(c.itertext()) for c in main_table(path).findall(".//w:tc", NS)]


def test_the_main_table_has_five_columns_in_the_grid_and_in_the_header_row(tmp_path):
    table = main_table(write(tmp_path, scenario_table()))

    assert len(table.findall("w:tblGrid/w:gridCol", NS)) == 5
    header = table.findall("w:tr", NS)[0]
    cells = ["".join(c.itertext()) for c in header.findall("w:tc", NS)]
    assert cells == COLUMNS


def test_the_first_row_is_a_header_row_that_repeats_and_no_other_row_is(tmp_path):
    rows = main_table(write(tmp_path, long_table(50))).findall("w:tr", NS)

    flags = [row.find("w:trPr/w:tblHeader", NS) is not None for row in rows]
    assert flags[0] is True
    assert not any(flags[1:])


def test_the_grid_has_the_widths_and_the_layout_is_fixed(tmp_path):
    table = main_table(write(tmp_path, scenario_table()))

    layout = table.find("w:tblPr/w:tblLayout", NS)
    assert layout is not None and layout.get(f"{{{W}}}type") == "fixed"
    widths = [int(c.get(f"{{{W}}}w")) for c in table.findall("w:tblGrid/w:gridCol", NS)]
    assert all(w > 0 for w in widths)
    assert widths[1] == max(widths)  # the activity column is the widest
    cell_widths = [
        int(c.find("w:tcPr/w:tcW", NS).get(f"{{{W}}}w"))
        for c in table.findall("w:tr", NS)[0].findall("w:tc", NS)
    ]
    assert cell_widths == widths


def test_the_page_is_a4_landscape(tmp_path):
    section = Document(str(write(tmp_path, scenario_table()))).sections[0]

    assert section.page_width > section.page_height
    assert round(section.page_width.mm) == 297
    assert round(section.page_height.mm) == 210


def test_the_footer_has_page_and_numpages_fields(tmp_path):
    path = write(tmp_path, scenario_table())

    footers = [n for n in zipfile.ZipFile(path).namelist() if n.startswith("word/footer")]
    assert footers
    footer = xml_of(path, footers[0])
    instructions = [t.text.strip() for t in footer.findall(".//w:instrText", NS)]
    assert instructions == ["PAGE", "NUMPAGES"]
    kinds = [c.get(f"{{{W}}}fldCharType") for c in footer.findall(".//w:fldChar", NS)]
    assert kinds == ["begin", "separate", "end", "begin", "separate", "end"]
    assert "Página" in "".join(footer.itertext())


def test_the_header_names_the_professor_the_classes_the_unit_the_interstice_and_the_table(
    tmp_path,
):
    text = text_of(write(tmp_path, scenario_table()))

    assert "Docente: Maria Docente da Silva" in text
    assert "Classe e nível atuais: Adjunto, nível 2" in text
    assert "Classe e nível pretendidos: Associado, nível 1" in text
    assert "Unidade: Faculdade de Testes" in text
    assert f"Interstício: {INTERSTICE_TEXT}" in text
    assert "Tabela de pontuação: Tabela de teste 2022" in text
    assert "Referência normativa: Res. de teste, Anexo I" in text


def test_a_group_without_activity_has_its_band_with_zero_and_the_bands_are_merged_cells(tmp_path):
    path = write(tmp_path, scenario_table())

    assert re.search(r"V\. Pesquisa Subtotal: 0,00", text_of(path))
    spans = main_table(path).findall(".//w:tc/w:tcPr/w:gridSpan", NS)
    assert len(spans) >= 2 * 7  # two merged cells in each of the seven bands (and the total row)
    assert {int(s.get(f"{{{W}}}val")) for s in spans} == {2, 3, 5}  # title, subtotal, total row


def test_the_counters_activities_and_divergences_and_the_rows_are_written(tmp_path):
    document = scenario_table()
    c = document.counters
    text = text_of(write(tmp_path, document))

    for part in (f"Atividades: {c.activities}", f"Com divergências: {c.with_alerts}", "II.3"):
        assert part in text


def test_no_cell_says_voucher_or_status_and_the_footer_has_no_voucher_nor_status_counters(
    tmp_path,
):
    # GTAB-04, GTAB-08
    path = write(tmp_path, scenario_table())
    cells = " ".join(cell_texts(path))
    footer = next(
        p.text for p in Document(str(path)).paragraphs if p.text.startswith("Atividades:")
    )

    for word in REMOVED_WORDS:
        assert word not in cells, word
    assert footer.count("|") == 1
    for word in ("Com comprovante", "Pendentes", "Não pontuadas"):
        assert word not in footer, word


def test_a_title_of_400_characters_and_a_seven_digit_subtotal_keep_the_band_in_two_cells(
    tmp_path,
):
    # GTAB-04: the band is one row with a cell for the title and one for the subtotal
    path = write(tmp_path, wide_band_table())

    rows = main_table(path).findall("w:tr", NS)
    band = ["".join(c.itertext()) for c in rows[1].findall("w:tc", NS)]
    assert band[1] == f"Subtotal: {BIG_SUBTOTAL}"
    assert "palavra0 palavra1" in text_of(path)
    title_cell = ["".join(c.itertext()) for c in rows[2].findall("w:tc", NS)][1]
    assert len(title_cell) == 400 and title_cell.endswith("…")


def test_the_total_and_the_subtotal_are_the_limited_ones_not_the_sum_of_the_rows(tmp_path):
    text = text_of(write(tmp_path, capped_table()))

    assert "160,00" in text  # the row of the ten orientations
    assert "Pontuação geral: 40,00" in text
    assert re.search(r"II\. [^:]*?Subtotal: 40,00", text)
    assert "Pontuação geral: 160,00" not in text


def test_each_counter_is_written_under_its_own_label(tmp_path):
    text = text_of(write(tmp_path, distinct_counters_table()))

    assert "Atividades: 21" in text
    assert "Com divergências: 2" in text


def test_the_pit_section_is_left_out_when_the_table_does_not_measure_hours(tmp_path):
    assert "Horas de PIT" not in text_of(write(tmp_path, replace(scenario_table(), pit_hours=None)))


def test_the_alerts_are_listed_with_the_activity_and_absent_when_there_are_none(tmp_path):
    alerts = (
        TableAlert("LIMITE_GRUPO", "Limite do grupo aplicado."),
        TableAlert("DATA_FIM_AUSENTE", "Data final ausente.", "Portaria de Diretor"),
    )

    with_alerts = text_of(write(tmp_path, replace(scenario_table(), alerts=alerts)))
    without = text_of(write(tmp_path, replace(scenario_table(), alerts=())))

    assert "Alertas" in with_alerts
    assert "Limite do grupo aplicado." in with_alerts
    assert "Portaria de Diretor: Data final ausente." in with_alerts
    assert "Alertas" not in without


def test_accents_and_characters_outside_basic_latin_come_out_as_written(tmp_path):
    text_value = "Zoë Ñandú ª ü ç Łukasz Őrdög Žižek Ωμέγα 日本語 & <b>"
    header = replace(HEADER, professor_name=text_value, unit_name="Faculdade ª ü ç")
    document = long_table(1)
    document = replace(document, header=header)
    band = document.bands[0]
    row = replace(band.rows[0], title=text_value)
    document = replace(document, bands=(replace(band, rows=(row,)), *document.bands[1:]))

    text = text_of(write(tmp_path, document))

    assert f"Docente: {text_value}" in text
    assert f"{text_value} 1,00" in text
    assert "Unidade: Faculdade ª ü ç" in text


def test_a_control_character_in_a_title_does_not_break_the_file(tmp_path):
    document = long_table(1, title="Título\x00 com\x0b controle\x1f")

    text = text_of(write(tmp_path, document))

    assert "Título com controle 0" in text


def test_a_thousand_rows_are_written_and_the_file_reads_back(tmp_path):
    path = write(tmp_path, long_table(1000))

    rows = main_table(path).findall("w:tr", NS)
    assert len(rows) >= 1000
    assert "Atividade sintética 999" in text_of(path)


def test_a_title_of_eight_thousand_characters_is_cut_in_the_docx_as_in_the_pdf(tmp_path):
    title = " ".join(f"palavra{n}" for n in range(1000))

    text = text_of(write(tmp_path, table_with_title(title)))

    assert "palavra0 palavra1" in text
    assert "palavra999" not in text
    assert "…" in text
