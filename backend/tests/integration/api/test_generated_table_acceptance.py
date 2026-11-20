"""TAB-01, TAB-04, TAB-05, TAB-06, TAB-07, TAB-08 (T89), GTAB-01 to GTAB-08: the scoring table of
the cenário derivado, asked through the API, downloaded as DOCX and PDF and read back: 211 pontos
on the previous version of the table (GI-06) and 303 pontos with section I on the seeded version.

The cenário derivado is the one of `test_scoring_golden.py` (subtotals II to VIII of 52, 7, 62, 0,
30, 4 and 56, total 211, PIT hours of 24, 24, 24 and 20, 92 in total), all synthetic.
"""

import re

import pytest

from tests.integration.api.generated_readers import docx_text, pdf_text, pt
from tests.integration.api.generated_support import ask, file_url, generate
from tests.integration.api.test_scoring_golden import add_derived_case, score
from tests.integration.api.test_scoring_golden import case as golden_case
from tests.integration.api.test_scoring_golden import case_303 as golden_case_303

SUBTOTALS = {"II": "52,00", "III": "7,00", "IV": "62,00", "V": "0,00", "VI": "30,00",
             "VII": "4,00", "VIII": "56,00"}  # fmt: skip
PIT_HOURS = ["24,00", "24,00", "24,00", "20,00"]
case = golden_case  # fixture of the cenário derivado (211): professor, process, official table
case_303 = golden_case_303  # the same on the seeded version, group I inside the total
GROUP_ONE_BAND = (
    "I. Docência/atividades de ensino/desempenho didático, "
    "avaliado com a participação do corpo discente"
)
HEADERS = "Item Atividade Quantidade Pontuação unitária Total"
NEW_HEADING = "Horas de PIT por semestre (Grupo I)"
OLD_HEADING = "Horas de PIT por semestre (Grupo I, fora do total de pontos)"
REMOVED_WORDS = ("Comprovante", "Status", "Pontuada", "Potencial", "Não pontuada",
                 "sem comprovante")  # fmt: skip
READERS = {"docx": docx_text, "pdf": pdf_text}


@pytest.fixture
def table_211(case):
    add_derived_case(case)
    row = generate(case["client"], case["headers"], case["process"], "TABELA")
    return case, row


@pytest.fixture
def table_303(case_303):
    add_derived_case(case_303)
    row = generate(case_303["client"], case_303["headers"], case_303["process"], "TABELA")
    return case_303, row


def text_303(table_303, extension) -> str:
    ctx, row = table_303
    return READERS[extension](ctx["client"].get(file_url(row, extension)).content)


def section_one(text: str) -> str:
    return text[text.index(GROUP_ONE_BAND) : text.index("II. ")]


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_new_version_has_section_i_with_the_subtotal_and_the_303_total(table_303, extension):
    # GTAB-01, GTAB-03
    text = text_303(table_303, extension)

    assert "Pontuação geral: 303,00" in text
    assert re.search(rf"{re.escape(GROUP_ONE_BAND)} Subtotal: 92,00", text)
    assert text.index(GROUP_ONE_BAND) < text.index("II. ")


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_section_i_has_one_row_per_offer_by_term_then_title_with_hours_one_point_and_total(
    table_303, extension
):
    # GTAB-02: twelve offers in four terms, by term then by title; hours, 1,00 and the same total
    section = section_one(text_303(table_303, extension))

    rows = re.findall(
        r"I\.1 Disciplina (\d) (2023\.\d) \((\d)\xba Per\xedodo de 2023\) "
        r"(\d+,\d\d) 1,00 (\d+,\d\d)",
        section,
    )

    expected = [(n, f"2023.{t}", t) for t in "1234" for n in "123"]
    assert [(r[0], r[1], r[2]) for r in rows] == expected
    assert [r[3] for r in rows] == ["8,00"] * 11 + ["4,00"]
    assert [r[4] for r in rows] == [r[3] for r in rows]
    assert "I.2 " not in section  # every offer is graduation


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_new_version_has_five_columns_the_new_hours_title_and_no_voucher_nor_status(
    table_303, extension
):
    # GTAB-04, GTAB-06, GTAB-08
    text = text_303(table_303, extension)

    assert HEADERS in text
    assert NEW_HEADING in text
    assert OLD_HEADING not in text
    for word in REMOVED_WORDS:
        assert word not in text, word
    pit = text[text.index(NEW_HEADING) :].split("Alertas")[0]
    assert re.findall(r"\b\d\d,00\b", pit) == [*PIT_HOURS, "92,00"]


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_previous_version_has_211_no_section_i_five_columns_and_the_old_hours_title(
    table_211, extension
):
    # GTAB-07
    ctx, row = table_211
    text = READERS[extension](ctx["client"].get(file_url(row, extension)).content)

    assert "Pontuação geral: 211,00" in text
    assert GROUP_ONE_BAND not in text
    assert HEADERS in text
    assert OLD_HEADING in text
    for word in REMOVED_WORDS:
        assert word not in text, word


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_downloaded_file_has_the_total_the_subtotals_and_the_pit_hours(table_211, extension):
    ctx, row = table_211

    download = ctx["client"].get(file_url(row, extension))

    assert download.status_code == 200
    text = READERS[extension](download.content)
    assert "Pontuação geral: 211,00" in text
    for numeral, subtotal in SUBTOTALS.items():
        assert re.search(rf"\b{numeral}\. [^:]*?Subtotal: {re.escape(subtotal)}", text), numeral
    pit = text[text.index("Horas de PIT") :].split("Alertas")[0]
    assert re.findall(r"\b\d\d,00\b", pit) == [*PIT_HOURS, "92,00"]


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_file_has_the_values_of_the_scoring_response(table_211, extension):
    ctx, row = table_211
    scored = score(ctx)

    text = READERS[extension](ctx["client"].get(file_url(row, extension)).content)

    assert f"Pontuação geral: {pt(scored['total'])}" in text
    for subtotal in scored["subtotals"][1:]:
        numeral = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"][subtotal["group_number"] - 1]
        pattern = rf"\b{numeral}\. [^:]*?Subtotal: {re.escape(pt(subtotal['subtotal']))}"
        assert re.search(pattern, text), numeral
    hours = [pt(v) for v in scored["group1_hours_by_period"].values()]
    pit = text[text.index("Horas de PIT") :].split("Alertas")[0]
    assert re.findall(r"\b\d\d,00\b", pit) == [*hours, pt(scored["group1_total_hours"])]
    assert f"Atividades: {scored['counters']['activities']}" in text


def test_the_snapshot_summary_of_the_version_is_the_scoring_response(table_211):
    ctx, row = table_211
    scored = score(ctx)

    summary = ctx["client"].get(f"/api/generated-documents/{row['id']}").json()["summary"]

    assert summary["total"] == scored["total"] == "211.00"
    assert summary["activity_count"] == scored["counters"]["activities"] == 38


def test_a_process_without_a_validated_activity_is_refused_with_the_code(case):
    response = ask(case["client"], case["headers"], case["process"], "TABELA")

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "SEM_ATIVIDADES_VALIDADAS")


def test_a_process_without_a_chosen_table_is_refused_with_the_code(
    client, admin, process, scoring_tables
):
    response = ask(client, admin[1], process, "TABELA")

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "TABELA_NAO_ESCOLHIDA")
