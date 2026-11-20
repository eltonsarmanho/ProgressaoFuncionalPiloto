"""TAB-01, TAB-04, TAB-05, TAB-06, TAB-07, TAB-08 (T89): the scoring table of the cenário derivado
(211 pontos), asked through the API, downloaded as DOCX and PDF and read back.

The cenário derivado is the one of `test_scoring_golden.py` (subtotals II to VIII of 52, 7, 62, 0,
30, 4 and 56, total 211, PIT hours of 24, 24, 24 and 20, 92 in total), all synthetic.
"""

import re

import pytest

from tests.integration.api.generated_readers import docx_text, pdf_text, pt
from tests.integration.api.generated_support import ask, file_url, generate
from tests.integration.api.test_scoring_golden import add_derived_case, score
from tests.integration.api.test_scoring_golden import case as golden_case

SUBTOTALS = {"II": "52,00", "III": "7,00", "IV": "62,00", "V": "0,00", "VI": "30,00",
             "VII": "4,00", "VIII": "56,00"}  # fmt: skip
PIT_HOURS = ["24,00", "24,00", "24,00", "20,00"]
case = golden_case  # fixture of the cenário derivado (211): professor, process, official table
READERS = {"docx": docx_text, "pdf": pdf_text}


@pytest.fixture
def table_211(case):
    add_derived_case(case)
    row = generate(case["client"], case["headers"], case["process"], "TABELA")
    return case, row


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
