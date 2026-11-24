"""EXT-07..13, PIPE-07 and the empty-list edge case: text to verified extraction."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.entities.document import DocAlertCode, DocumentStatus
from app.domain.entities.extraction import DocumentType, TaxonomyCode
from app.domain.repositories.ports import AiExtractionError
from app.domain.rules.interstice import Interstice
from app.domain.rules.upload_validation import FileKind
from app.infrastructure.ai.schemas import validate_response
from tests.unit.application.analyzer_fakes import (
    BANCA_TEXT,
    PROFESSOR,
    SIAPE,
    FakeAi,
    FakeTextExtractor,
    StepClock,
    activity,
    analyzer,
    ocr_page,
    payload,
    run,
    text_page,
)


def codes(result, code=None):
    return [a.code for a in result.alerts if code is None or a.code is code]


def analyze(ai_answer, *pages, **kwargs):
    extractor = FakeTextExtractor(*(pages or (text_page(1),)))
    ai = FakeAi(ai_answer) if not isinstance(ai_answer, FakeAi) else ai_answer
    return run(analyzer(extractor, ai), **kwargs), ai


# --- what is sent to the AI (EXT-07, EXT-08) -------------------------------------------


def test_text_sent_to_the_ai_is_masked_but_keeps_names_and_siape():
    text = (
        f"{PROFESSOR}, SIAPE {SIAPE}, CPF 000.000.000-00, e-mail fulana@example.test, "
        "telefone (11) 91234-5678."
    )
    result, ai = analyze(payload(), text_page(1, text))
    sent = ai.calls[0][1]
    assert "[CPF]" in sent and "[EMAIL]" in sent and "[TELEFONE]" in sent
    assert "000.000.000-00" not in sent
    assert "fulana@example.test" not in sent
    assert PROFESSOR in sent and f"SIAPE {SIAPE}" in sent
    assert result.pages[0].text == text  # the stored text keeps the original


def test_the_professor_name_goes_to_the_ai_and_the_identifiers_do_not():
    text = f"{PROFESSOR}, SIAPE {SIAPE}, CPF 000.000.000-00, participou da banca."
    _, ai = analyze(payload(), text_page(1, text))
    _, sent, professor = ai.calls[0]
    assert professor == PROFESSOR
    assert "000.000.000-00" not in sent and "000.000.000-00" not in professor
    assert SIAPE not in professor


def test_the_professor_name_is_sent_again_on_the_new_attempt_after_an_invalid_answer():
    _, ai = analyze(FakeAi({"documento": "invalido"}, payload()))
    assert [call[2] for call in ai.calls] == [PROFESSOR, PROFESSOR]


def test_text_sent_carries_the_page_markers():
    _, ai = analyze(payload(), text_page(1, "primeira"), text_page(2, "segunda"))
    assert ai.calls[0][1] == "[PÁGINA 1]\nprimeira\n\n[PÁGINA 2]\nsegunda"


def test_only_the_first_six_pages_are_sent_and_truncated_is_flagged():
    pages = [text_page(n, f"texto da pagina numero {n}") for n in range(1, 9)]
    result, ai = analyze(payload(), *pages)
    sent = ai.calls[0][1]
    assert "[PÁGINA 6]" in sent
    assert "[PÁGINA 7]" not in sent and "pagina numero 7" not in sent
    assert codes(result, DocAlertCode.TRUNCADO) == [DocAlertCode.TRUNCADO]
    assert len(result.pages) == 8  # every page stays available for storage


def test_exactly_six_pages_are_not_truncated():
    pages = [text_page(n, f"texto da pagina numero {n}") for n in range(1, 7)]
    result, _ = analyze(payload(), *pages)
    assert DocAlertCode.TRUNCADO not in codes(result)


def test_the_schema_type_comes_from_the_keyword_rule():
    result, ai = analyze(payload())
    assert ai.calls[0][0] is DocumentType.DECLARACAO_BANCA
    assert result.document_type is DocumentType.DECLARACAO_BANCA


def test_unrecognized_text_uses_the_generic_type():
    result, ai = analyze(payload(), text_page(1, "texto qualquer sem relacao com nada importante"))
    assert ai.calls[0][0] is DocumentType.OUTRO
    assert result.document_type is DocumentType.OUTRO


# --- the AI that invents data is caught (EXT-10) ----------------------------------------


def test_an_invented_date_becomes_null_with_a_warning_naming_the_field():
    result, _ = analyze(payload(activity(event_date="2031-07-04")))
    found = result.activities[0].extracted
    assert found.event_date is None
    assert [(a.code, a.field) for a in result.alerts] == [
        (DocAlertCode.NAO_ENCONTRADO_NO_TEXTO, "event_date")
    ]
    assert result.alerts[0].activity_index == 0
    assert found.title == "Estudo Ficticio sobre Dados Abertos"  # the true field survives


def test_invented_hours_title_and_identifier_are_nulled_one_warning_each():
    invented = activity(
        hours=999, course_hours=888, title="Livro Inexistente de Fisica Quantica", identifier="ZZ99"
    )
    result, _ = analyze(payload(invented))
    found = result.activities[0].extracted
    assert (found.hours, found.course_hours, found.title, found.identifier) == (None,) * 4
    fields = sorted(a.field for a in result.alerts)
    assert codes(result) == [DocAlertCode.NAO_ENCONTRADO_NO_TEXTO] * 4
    assert fields == ["course_hours", "hours", "identifier", "title"]


def test_a_value_present_only_on_another_page_is_nulled():
    pages = (text_page(1, BANCA_TEXT), text_page(2, "Carga horaria de 40 horas no total geral."))
    result, _ = analyze(payload(activity(hours=40, page=1)), *pages)
    assert result.activities[0].extracted.hours is None
    warned = [(a.code, a.field) for a in result.alerts]
    assert (DocAlertCode.NAO_ENCONTRADO_NO_TEXTO, "hours") in warned


def test_a_value_on_the_cited_page_is_kept():
    pages = (text_page(1, "outra coisa sem nada relevante aqui"), text_page(2, BANCA_TEXT))
    result, _ = analyze(payload(activity(page=2)), *pages)
    assert str(result.activities[0].extracted.event_date) == "2025-03-12"
    assert result.alerts == ()


def test_an_activity_citing_a_page_that_was_not_sent_loses_every_value():
    result, _ = analyze(payload(activity(page=9)))
    found = result.activities[0]
    assert found.extracted.title is None and found.extracted.event_date is None
    assert found.confidence == Decimal("0.00")
    assert found.needs_review is True


def test_each_activity_is_grounded_on_its_own():
    good = activity()
    bad = activity(event_date="2020-01-01")
    result, _ = analyze(payload(good, bad))
    assert result.activities[0].extracted.event_date is not None
    assert result.activities[1].extracted.event_date is None
    assert [a.activity_index for a in result.alerts] == [1]


# --- the professor (EXT-11) --------------------------------------------------------------


def test_another_professor_raises_the_alert_and_requires_review():
    result, _ = analyze(payload(activity(), name="Beltrana da Silva Outra"), text_page(1, "x" * 60))
    assert DocAlertCode.DOCENTE_DIVERGENTE in codes(result)
    assert result.status is DocumentStatus.REQUER_REVISAO


def test_matching_name_keeps_the_document_processed():
    result, _ = analyze(payload(activity()))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)
    assert result.status is DocumentStatus.PROCESSADO
    assert result.status_code is None


def test_different_name_but_the_siape_in_the_text_is_not_a_divergence():
    text = f"Declaramos que Outra Pessoa Qualquer, SIAPE {SIAPE}, participou da banca."
    result, _ = analyze(payload(name="Outra Pessoa Qualquer"), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)


def test_no_name_extracted_and_the_professor_not_in_the_text_is_a_divergence():
    text = "Declaramos que alguem participou da banca examinadora em 12 de marco de 2025."
    result, _ = analyze(payload(name=None), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE in codes(result)


def test_no_name_extracted_but_the_professor_in_the_text_is_not_a_divergence():
    result, _ = analyze(payload(name=None))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)


def test_ai_returns_a_student_but_the_professor_is_named_in_the_text_is_no_divergence():
    text = (
        "ATA DE DEFESA. Discente: Joana Imaginaria Costa. Banca examinadora: "
        f"Prof. {PROFESSOR} (presidente), Prof. Carlos Ficticio Lima (membro). "
        "A defesa ocorreu em 12 de marco de 2025."
    )
    result, _ = analyze(payload(activity(), name="Joana Imaginaria Costa"), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)
    assert result.status is DocumentStatus.PROCESSADO


def test_ai_returns_the_president_but_the_professor_is_a_listed_member_is_no_divergence():
    text = (
        "PORTARIA. Designar os servidores Carlos Ficticio Lima (presidente) e "
        "EXEMPLO, Fulana de Tal (membro) para a comissao, a partir de 12 de marco de 2025."
    )
    result, _ = analyze(payload(activity(), name="Carlos Ficticio Lima"), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)


def test_ai_returns_another_person_and_the_professor_name_is_scattered_is_a_divergence():
    text = (
        "Fulana Beltrana presidiu. Maria de Tal assistiu a sessao, e o Prof. Pedro Exemplo "
        "apresentou o trabalho de Ana de Tal na sala 12 do predio principal."
    )
    result, _ = analyze(payload(activity(), name="Fulana Beltrana"), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE in codes(result)
    assert result.status is DocumentStatus.REQUER_REVISAO


def test_abbreviated_ai_name_of_the_professor_is_no_divergence():
    text = "Participaram da banca os docentes F. T. Exemplo e Carlos Lima, em 12 de marco de 2025."
    result, _ = analyze(payload(activity(), name="F. T. Exemplo"), text_page(1, text))
    assert DocAlertCode.DOCENTE_DIVERGENTE not in codes(result)


def test_abbreviated_ai_name_of_a_homonym_is_a_divergence():
    # VER-13: "M. A. Souza" fits the initials of Marcos Antonio Souza, but the page names
    # Maria Aparecida Souza and never the abbreviated form nor the professor
    text = "A banca teve Maria Aparecida Souza como presidente, em 12 de marco de 2025."
    result, _ = analyze(
        payload(activity(), name="M. A. Souza"),
        text_page(1, text),
        professor="Marcos Antonio Souza",
    )
    assert DocAlertCode.DOCENTE_DIVERGENTE in codes(result)
    assert result.status is DocumentStatus.REQUER_REVISAO


# --- repeated activities of one document (REAL-07) --------------------------------------------


def test_six_identical_activities_on_the_same_page_become_one():
    same = activity(event_date=None)
    result, _ = analyze(payload(*[dict(same) for _ in range(6)]))
    assert len(result.activities) == 1
    assert codes(result, DocAlertCode.ATIVIDADE_REPETIDA) == [DocAlertCode.ATIVIDADE_REPETIDA] * 5
    repeated = [a for a in result.alerts if a.code is DocAlertCode.ATIVIDADE_REPETIDA]
    assert sorted(a.activity_index for a in repeated) == [1, 2, 3, 4, 5]


def test_identical_activities_with_the_same_date_become_one():
    result, _ = analyze(payload(activity(), activity()))
    assert len(result.activities) == 1
    assert result.activities[0].source_index == 0


def test_title_is_compared_without_case_accent_or_extra_spaces():
    first = activity(title="Estudo Fictício  sobre Dados Abertos")
    second = activity(title="ESTUDO FICTICIO sobre dados abertos")
    result, _ = analyze(payload(first, second))
    assert len(result.activities) == 1


def test_a_dated_and_an_undated_copy_collapse_and_keep_the_dated_one():
    result, _ = analyze(payload(activity(event_date=None), activity()))
    assert len(result.activities) == 1
    assert result.activities[0].extracted.event_date == date(2025, 3, 12)


def test_different_dates_that_do_not_overlap_stay_separate():
    text = BANCA_TEXT + " Nova sessao em 20 de marco de 2025."
    result, _ = analyze(payload(activity(), activity(event_date="2025-03-20")), text_page(1, text))
    assert len(result.activities) == 2
    assert DocAlertCode.ATIVIDADE_REPETIDA not in codes(result)


def test_different_titles_items_or_pages_stay_separate():
    other_title = activity(title="Analise de Redes Sociais")  # TER-07: "Estudo Ficticio" is inside
    other_item = activity(taxonomy="BANCA_MESTRADO")
    result, _ = analyze(payload(activity(), other_title, other_item))
    assert len(result.activities) == 3

    pages = (text_page(1), text_page(2))
    result, _ = analyze(payload(activity(), activity(page=2)), *pages)
    assert len(result.activities) == 2


# --- portaria clauses that dismiss the professor (REAL-10) --------------------------------

PORTARIA_TEXT = (
    "PORTARIA Nº 100. Art. 1º DESIGNAR Fulana de Tal Exemplo para exercer a função de "
    "Vice-Diretora da Faculdade Exemplo, a partir de 09 de agosto de 2026. "
    "Art. 2º DISPENSAR Fulana de Tal Exemplo da função de Diretora da Faculdade Exemplo."
)


def portaria_activity(taxonomy, evidence):
    return activity(
        taxonomy=taxonomy, title=None, event_date=None, evidence_text=evidence, role="cargo"
    )


def test_dismissal_clause_creates_no_activity_but_the_designation_does():
    designation = portaria_activity(
        "FUNCAO_VICE_DIRETOR_FACULDADE",
        "DESIGNAR Fulana de Tal Exemplo para exercer a função de Vice-Diretora",
    )
    dismissal = portaria_activity(
        "FUNCAO_DIRETOR_FACULDADE",
        "DISPENSAR Fulana de Tal Exemplo da função de Diretora da Faculdade Exemplo",
    )
    result, _ = analyze(
        payload(designation, dismissal, document_type="PORTARIA"), text_page(1, PORTARIA_TEXT)
    )
    assert [a.taxonomy.value for a in result.activities] == ["FUNCAO_VICE_DIRETOR_FACULDADE"]
    dispensed = [a for a in result.alerts if a.code is DocAlertCode.CLAUSULA_DE_DISPENSA]
    assert [a.activity_index for a in dispensed] == [1]
    assert DocAlertCode.SEM_ITEM_DE_PONTUACAO not in codes(result)


# --- yearly items count complete years of exercise inside the interstice (REAL-11) ---------

INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))


def designation(start, end, taxonomy="FUNCAO_VICE_DIRETOR_FACULDADE"):
    return activity(
        taxonomy=taxonomy, title=None, event_date=None, start_date=start, end_date=end,
        evidence_text="DESIGNAR Fulana de Tal Exemplo",
    )  # fmt: skip


def test_three_months_of_exercise_do_not_become_a_full_year():
    text = (
        "PORTARIA. DESIGNAR Fulana de Tal Exemplo como Vice-Diretora da Faculdade, de "
        "09/08/2026 a 23/11/2026."
    )
    raw = designation("2026-08-09", "2026-11-23")
    result, _ = analyze(
        payload(raw, document_type="PORTARIA"), text_page(1, text), interstice=INTERSTICE
    )
    [suggested] = result.activities
    assert suggested.quantity == Decimal(0)
    assert DocAlertCode.QUANTIDADE_ESTIMADA in codes(result)


def test_exercise_years_are_counted_inside_the_interstice():
    text = (
        "PORTARIA. DESIGNAR Fulana de Tal Exemplo como Vice-Diretora da Faculdade, "
        "de 09/08/2023 a 09/08/2027."
    )
    raw = designation("2023-08-09", "2027-08-09")
    result, _ = analyze(
        payload(raw, document_type="PORTARIA"), text_page(1, text), interstice=INTERSTICE
    )
    assert result.activities[0].quantity == Decimal(2)


# --- extension projects need the word "extensão" (REAL-12) -------------------------------

POLICY_BRIEF = (
    "CERTIFICADO. Certificamos que Fulana de Tal Exemplo participou do projeto Policy Brief "
    "sobre Dados Abertos, com carga horaria de 18 horas, em 12 de marco de 2025."
)


def project_activity(**changes):
    base = {
        "taxonomy": "EXTENSAO_PROJETO_PARTICIPACAO",
        "title": "Policy Brief sobre Dados Abertos",
        "event_date": "2025-03-12",
        "hours": 18,
        "evidence_text": "participou do projeto Policy Brief",
    }
    return activity(**(base | changes))


def test_certificate_of_a_project_without_the_word_extension_is_a_short_course_with_hours():
    """CER-02: with its 18 hours the certificate is VII.10, flagged; it was dropped before."""
    result, _ = analyze(
        payload(project_activity(), document_type="CERTIFICADO"), text_page(1, POLICY_BRIEF)
    )
    [suggested] = result.activities
    assert (suggested.group_number, suggested.item_number) == (7, 10)
    assert suggested.needs_review is True
    assert codes(result, DocAlertCode.ENQUADRADO_COMO_CAPACITACAO) == [
        DocAlertCode.ENQUADRADO_COMO_CAPACITACAO
    ]
    assert codes(result, DocAlertCode.SEM_ITEM_DE_PONTUACAO) == []
    assert result.status is DocumentStatus.PROCESSADO


def test_certificate_of_a_project_without_the_word_extension_and_hours_gets_no_item():
    text = POLICY_BRIEF.replace(", com carga horaria de 18 horas", "")
    result, _ = analyze(
        payload(project_activity(hours=None), document_type="CERTIFICADO"), text_page(1, text)
    )
    assert result.activities == ()
    assert codes(result, DocAlertCode.SEM_ITEM_DE_PONTUACAO) == [DocAlertCode.SEM_ITEM_DE_PONTUACAO]
    assert result.status is DocumentStatus.PROCESSADO


def test_certificate_of_a_project_that_says_extension_keeps_item_iv_2():
    text = POLICY_BRIEF.replace("projeto Policy", "projeto de Extensao Policy")
    result, _ = analyze(
        payload(project_activity(), document_type="CERTIFICADO"), text_page(1, text)
    )
    [suggested] = result.activities
    assert (suggested.group_number, suggested.item_number) == (4, 2)


# --- per-action items count one per distinct action (VER-12) -----------------------------

TWO_PROJECTS = (
    "CERTIFICADO. Certificamos que Fulana de Tal Exemplo participou do projeto de extensão "
    "Alfa Ficticio de 01/02/2023 a 31/01/2025 e do projeto de extensão Beta Ficticio de "
    "01/03/2023 a 28/02/2025."
)


def extension_project(title, start, end):
    return activity(
        taxonomy="EXTENSAO_PROJETO_PARTICIPACAO",
        title=title,
        event_date=None,
        start_date=start,
        end_date=end,
        hours=None,
        evidence_text=f"participou do projeto de extensão {title}",
    )


def test_two_distinct_extension_projects_count_one_action_each_not_years():
    alfa = extension_project("Alfa Ficticio", "2023-02-01", "2025-01-31")
    beta = extension_project("Beta Ficticio", "2023-03-01", "2025-02-28")

    result, _ = analyze(
        payload(alfa, beta, document_type="CERTIFICADO"),
        text_page(1, TWO_PROJECTS),
        interstice=INTERSTICE,
    )

    assert [a.quantity for a in result.activities] == [Decimal(1), Decimal(1)]
    assert DocAlertCode.QUANTIDADE_ESTIMADA not in codes(result)


def test_the_same_extension_project_listed_twice_counts_one_action():
    alfa = extension_project("Alfa Ficticio", "2023-02-01", "2025-01-31")

    result, _ = analyze(
        payload(alfa, alfa, document_type="CERTIFICADO"),
        text_page(1, TWO_PROJECTS),
        interstice=INTERSTICE,
    )

    assert [a.quantity for a in result.activities] == [Decimal(1)]
    assert codes(result, DocAlertCode.ATIVIDADE_REPETIDA) == [DocAlertCode.ATIVIDADE_REPETIDA]


# --- seminar evaluation forms are not boards (REAL-18) -----------------------------------

SEMINAR_FORM = (
    "FICHA DE AVALIAÇÃO DE SEMINÁRIO 2. Discente: Joao Inventado. Avaliador 1: Prof. "
    "Fulana de Tal Exemplo, nota 9,0. Avaliador 2: Prof. Carlos Imaginario, nota 8,5. "
    "Seminário apresentado em 12 de marco de 2025."
)


def test_seminar_form_read_by_the_ai_as_masters_boards_creates_no_activity():
    boards = [
        activity(taxonomy="BANCA_MESTRADO", title=None, evidence_text=f"Avaliador {n}")
        for n in (1, 2)
    ]
    result, _ = analyze(payload(*boards, document_type="OUTRO"), text_page(1, SEMINAR_FORM))
    assert result.document_type is DocumentType.OUTRO
    assert result.activities == ()
    assert codes(result, DocAlertCode.SEM_ITEM_DE_PONTUACAO)


def test_a_real_defense_minutes_still_makes_the_master_board():
    text = (
        "ATA DA DEFESA DE DISSERTACAO. A banca examinadora composta por Fulana de Tal Exemplo "
        "aprovou o trabalho Estudo Ficticio sobre Dados Abertos em 12 de marco de 2025."
    )
    board = activity(taxonomy="BANCA_MESTRADO", evidence_text="banca examinadora composta")
    result, _ = analyze(payload(board, document_type="ATA_DEFESA"), text_page(1, text))
    assert [a.group_number for a in result.activities] == [3]
    assert [a.item_number for a in result.activities] == [2]


# --- invalid answers (EXT-09) -------------------------------------------------------------

OUT_OF_SCHEMA = [
    payload(activity()) | {"pontos": 3},
    payload(activity(pontuacao=3)),
    payload({k: v for k, v in activity().items() if k != "title"}),
    payload(activity(taxonomy="INVENTADA")),
    payload(activity(page="1")),
    payload(activity(hours="68")),
    payload(activity(level="MEDIO")),
    payload(document_type="PIADA"),
    {"document_type": "OUTRO", "docente_nome": None},
    {"document_type": "OUTRO", "docente_nome": None, "activities": {}},
    payload(activity(confidence=None)),
]


@pytest.mark.parametrize("bad", OUT_OF_SCHEMA)
def test_every_json_schema_violation_is_also_refused_by_the_analyzer(bad):
    assert validate_response(DocumentType.DECLARACAO_BANCA, bad) != []
    result, ai = analyze(bad)
    assert result.status is DocumentStatus.REQUER_REVISAO
    assert result.status_code == "RESPOSTA_INVALIDA"
    assert len(ai.calls) == 2


@pytest.mark.parametrize(
    "bad",
    [
        payload(activity(event_date="12/03/2025")),
        payload(activity(event_date="2025-13-40")),
        payload(activity(confidence=1.5)),
        payload(activity(confidence=-0.1)),
        payload(activity(hours=-3)),
        payload(activity(page=0)),
        payload(activity(page=True)),
    ],
)
def test_values_the_schema_cannot_bound_are_refused_by_the_analyzer(bad):
    result, ai = analyze(bad)
    assert result.status_code == "RESPOSTA_INVALIDA"
    assert len(ai.calls) == 2


def test_a_valid_payload_passes_both_the_schema_and_the_analyzer():
    good = payload(activity())
    assert validate_response(DocumentType.DECLARACAO_BANCA, good) == []
    result, ai = analyze(good)
    assert result.status is DocumentStatus.PROCESSADO
    assert len(ai.calls) == 1


def test_invalid_json_gets_one_new_attempt_that_can_succeed():
    ai = FakeAi(payload(activity()) | {"extra": 1}, payload(activity()))
    result, _ = analyze(ai)
    assert len(ai.calls) == 2
    assert result.status is DocumentStatus.PROCESSADO
    assert len(result.activities) == 1


def test_invalid_json_twice_requires_review_with_resposta_invalida_and_keeps_the_last_raw():
    first, last = payload(activity()) | {"a": 1}, payload(activity()) | {"b": 2}
    result, ai = analyze(FakeAi(first, last))
    assert result.status is DocumentStatus.REQUER_REVISAO
    assert result.status_code == "RESPOSTA_INVALIDA"
    assert codes(result) == [DocAlertCode.RESPOSTA_INVALIDA]
    assert result.activities == ()
    assert result.raw_json == last
    assert len(ai.calls) == 2


def test_provider_error_resposta_invalida_requires_review_without_a_new_attempt():
    result, ai = analyze(FakeAi(AiExtractionError(DocAlertCode.RESPOSTA_INVALIDA)))
    assert result.status is DocumentStatus.REQUER_REVISAO
    assert result.status_code == "RESPOSTA_INVALIDA"
    assert codes(result) == [DocAlertCode.RESPOSTA_INVALIDA]
    assert len(ai.calls) == 1
    assert result.raw_json is None


@pytest.mark.parametrize(
    "code", [DocAlertCode.IA_CREDENCIAL_RECUSADA, DocAlertCode.IA_INDISPONIVEL]
)
def test_unavailable_ai_gives_extraido_sem_ia_and_keeps_the_text(code):
    result, ai = analyze(FakeAi(AiExtractionError(code)))
    assert result.status is DocumentStatus.EXTRAIDO_SEM_IA
    assert result.status_code == code.value
    assert codes(result) == [code]
    assert result.activities == ()
    assert result.pages[0].text == BANCA_TEXT
    assert len(ai.calls) == 1


# --- empty list, confidence and the stored record -----------------------------------------


def test_empty_activity_list_on_a_readable_document_is_processed_with_the_warning():
    result, _ = analyze(payload())
    assert result.status is DocumentStatus.PROCESSADO
    assert result.status_code is None
    assert result.activities == ()
    assert codes(result) == [DocAlertCode.NENHUMA_ATIVIDADE_ENCONTRADA]


@pytest.mark.parametrize(
    ("llm", "expected", "review"),
    [(0.95, "0.95", False), (0.7, "0.70", False), (0.69, "0.69", True), (0.3, "0.30", True)],
)
def test_final_confidence_is_the_lower_of_ai_value_and_found_fraction(llm, expected, review):
    result, _ = analyze(payload(activity(confidence=llm)))
    found = result.activities[0]
    assert found.confidence == Decimal(expected)
    assert found.needs_review is review


def test_found_fraction_below_the_ai_confidence_lowers_it():
    result, _ = analyze(payload(activity(event_date="2031-07-04", confidence=0.99)))
    found = result.activities[0]  # title found, date not: 1 of 2
    assert found.confidence == Decimal("0.50")
    assert found.needs_review is True


def test_activity_with_nothing_verifiable_requires_review():
    bare = activity(title=None, event_date=None, confidence=0.99)
    found = analyze(payload(bare))[0].activities[0]
    assert found.confidence == Decimal("0.00")
    assert found.needs_review is True


def test_result_carries_raw_json_model_and_duration():
    answer = payload(activity())
    result, _ = analyze(FakeAi(answer, model="sabiazinho-4"))
    assert result.raw_json == answer
    assert result.model == "sabiazinho-4"
    assert result.duration_ms == 1500


def test_suggested_activity_keeps_taxonomy_page_and_a_real_excerpt():
    result, _ = analyze(payload(activity()))
    found = result.activities[0]
    assert found.taxonomy is TaxonomyCode.BANCA_TCC_GRADUACAO
    assert found.page == 1
    assert found.excerpt == "participou como membro da banca examinadora"
    assert found.excerpt in " ".join(BANCA_TEXT.split())


def test_excerpt_is_cut_at_300_characters_of_the_page_text():
    long_page = "Declaramos " + "palavra " * 100 + "fim."
    quote = "palavra " * 60
    result, _ = analyze(payload(activity(evidence_text=quote)), text_page(1, long_page))
    assert len(result.activities[0].excerpt) == 300
    assert result.activities[0].excerpt in " ".join(long_page.split())


def test_excerpt_of_a_quote_missing_from_the_page_comes_from_the_page_start():
    result, _ = analyze(payload(activity(evidence_text="frase que o modelo inventou")))
    excerpt = result.activities[0].excerpt
    assert "inventou" not in excerpt
    assert excerpt == " ".join(BANCA_TEXT.split())[:300]


def test_excerpt_ignores_line_breaks_and_case_in_the_page():
    text = "Declaramos que\nFULANA participou\ncomo membro da banca"
    result, _ = analyze(payload(activity(evidence_text="fulana participou como membro")),
                        text_page(1, text))
    assert result.activities[0].excerpt == "FULANA participou como membro"


# --- text extraction outcomes (PIPE-07, PIPE-08) -------------------------------------------


def test_extraction_timeout_fails_the_document_and_keeps_the_pages_read():
    extractor = FakeTextExtractor(text_page(1), timed_out=True)
    ai = FakeAi(payload())
    result = run(analyzer(extractor, ai))
    assert result.status is DocumentStatus.FALHOU
    assert result.status_code == "TEMPO_ESGOTADO"
    assert codes(result) == [DocAlertCode.TEMPO_ESGOTADO]
    assert len(result.pages) == 1
    assert ai.calls == []


@pytest.mark.parametrize("confidence", ["59.99", "10", "0"])
def test_low_mean_ocr_confidence_requires_review_as_illegible_without_calling_the_ai(confidence):
    result, ai = analyze(payload(), ocr_page(1, BANCA_TEXT, confidence))
    assert result.status is DocumentStatus.REQUER_REVISAO
    assert result.status_code == "TEXTO_ILEGIVEL"
    assert codes(result) == [DocAlertCode.TEXTO_ILEGIVEL]
    assert ai.calls == []
    assert result.pages[0].text == BANCA_TEXT


def test_ocr_confidence_of_exactly_60_is_legible():
    result, ai = analyze(payload(), ocr_page(1, BANCA_TEXT, "60"))
    assert DocAlertCode.TEXTO_ILEGIVEL not in codes(result)
    assert len(ai.calls) == 1


def test_mean_confidence_is_taken_over_the_ocr_pages():
    pages = (ocr_page(1, BANCA_TEXT, "90"), ocr_page(2, "texto da segunda pagina aqui", "40"))
    result, _ = analyze(payload(), *pages)
    assert DocAlertCode.TEXTO_ILEGIVEL not in codes(result)  # mean 65
    pages = (ocr_page(1, BANCA_TEXT, "90"), ocr_page(2, "texto da segunda pagina aqui", "20"))
    result, _ = analyze(payload(), *pages)
    assert DocAlertCode.TEXTO_ILEGIVEL in codes(result)  # mean 55


@pytest.mark.parametrize("pages", [(), (text_page(1, ""),), (text_page(1, "   \n "),)])
def test_no_text_at_all_is_illegible(pages):
    extractor = FakeTextExtractor(*pages)
    ai = FakeAi(payload())
    result = run(analyzer(extractor, ai))
    assert result.status is DocumentStatus.REQUER_REVISAO
    assert result.status_code == "TEXTO_ILEGIVEL"
    assert ai.calls == []


def test_text_layer_pages_are_not_illegible_even_without_ocr_confidence():
    result, ai = analyze(payload(), text_page(1))
    assert DocAlertCode.TEXTO_ILEGIVEL not in codes(result)
    assert len(ai.calls) == 1


def test_the_analyzer_passes_path_and_kind_to_the_text_extractor():
    extractor = FakeTextExtractor(text_page(1))
    analyzer(extractor, FakeAi(payload())).analyze(
        Path("/x/y.png"), FileKind.PNG, PROFESSOR, SIAPE, None, None
    )
    assert [(str(p), k) for p, k in extractor.calls] == [("/x/y.png", FileKind.PNG)]


def test_clock_reads_decide_the_duration():
    extractor = FakeTextExtractor(text_page(1))
    result = run(analyzer(extractor, FakeAi(payload()), StepClock(step_ms=250)))
    assert result.duration_ms == 250
