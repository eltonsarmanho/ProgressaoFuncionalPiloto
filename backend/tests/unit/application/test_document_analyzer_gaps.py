"""SEG-11: repeated activities and the text the rules read (X02, X03, X05, X07, X08)."""

from app.domain.entities.document import DocAlertCode, DocumentStatus
from app.domain.entities.extraction import TaxonomyCode
from tests.unit.application.analyzer_fakes import (
    PROFESSOR,
    FakeAi,
    FakeTextExtractor,
    activity,
    analyzer,
    payload,
    run,
    text_page,
)


def analyze(items, *pages, name=PROFESSOR, document_type="OUTRO"):
    ai = FakeAi(payload(*items, name=name, document_type=document_type))
    return run(analyzer(FakeTextExtractor(*pages), ai))


def repeated(result):
    return [a.activity_index for a in result.alerts if a.code is DocAlertCode.ATIVIDADE_REPETIDA]


# X02: without a title the evidence tells two activities apart.
def test_activities_without_a_title_and_with_different_evidence_stay_apart():
    one = activity(title=None, event_date=None, evidence_text="participou da primeira reuniao")
    two = activity(title=None, event_date=None, evidence_text="participou da segunda reuniao")
    text = f"{PROFESSOR} participou da primeira reuniao e participou da segunda reuniao."
    result = analyze([one, two], text_page(1, text))
    assert len(result.activities) == 2
    assert repeated(result) == []


def test_activities_without_a_title_and_with_the_same_evidence_are_one():
    one = activity(title=None, event_date=None, evidence_text="participou da reuniao")
    result = analyze([one, dict(one)], text_page(1, f"{PROFESSOR} participou da reuniao."))
    assert len(result.activities) == 1
    assert repeated(result) == [1]


# X03: the level is part of the identity of a course.
def test_the_same_course_title_at_two_levels_is_two_activities():
    base = {
        "taxonomy": "DISCIPLINA_MINISTRADA",
        "title": "Algoritmos",
        "event_date": None,
        "hours": 60,
        "evidence_text": "Algoritmos 60 horas",
    }
    graduation = activity(**base, level="GRADUACAO")
    postgraduate = activity(**base, level="POS_GRADUACAO")
    text = f"{PROFESSOR} ministrou Algoritmos, 60 horas, na graduacao e na pos-graduacao."
    result = analyze([graduation, postgraduate], text_page(1, text))
    assert [(s.group_number, s.item_number) for s in result.activities] == [(1, 1), (1, 2)]
    assert repeated(result) == []


# X05: a period with only a start or only an end is dated, not undated.
def half_open(**changes):
    base = {
        "taxonomy": "COLEGIADO_MEMBRO",
        "title": "Colegiado do Curso",
        "event_date": None,
        "evidence_text": "membro do Colegiado do Curso",
    }
    return activity(**(base | changes))


TEXT_DATES = f"{PROFESSOR} e membro do Colegiado do Curso desde 10/01/2025 e 10/09/2025."


def test_half_open_periods_on_different_dates_stay_apart():
    one = half_open(start_date="2025-01-10")
    two = half_open(start_date="2025-09-10")
    result = analyze([one, two], text_page(1, TEXT_DATES))
    assert len(result.activities) == 2
    assert repeated(result) == []


def test_half_open_periods_on_the_same_date_are_one():
    one = half_open(start_date="2025-01-10")
    two = half_open(end_date="2025-01-10")
    result = analyze([one, two], text_page(1, TEXT_DATES))
    assert len(result.activities) == 1
    assert repeated(result) == [1]


# X07: the rules read the whole document, the AI only the first pages.
def test_the_extension_wording_after_the_pages_sent_to_the_ai_still_counts():
    item = activity(
        taxonomy="CURSO_EXTENSAO_CONCLUIDO",
        title="Boas Praticas de Dados",
        event_date=None,
        evidence_text="concluiu o curso",
    )
    first = f"Certificamos que {PROFESSOR} concluiu o curso Boas Praticas de Dados."
    pages = [text_page(1, first)] + [text_page(n, f"Pagina {n} sem nada.") for n in range(2, 7)]
    pages.append(text_page(7, "Regulamento do curso de extensão da universidade."))
    result = analyze([item], *pages, document_type="CERTIFICADO")
    assert DocAlertCode.TRUNCADO in [a.code for a in result.alerts]
    assert result.activities[0].taxonomy is TaxonomyCode.CURSO_EXTENSAO_CONCLUIDO


# X08: the professor named on a later page is still the professor.
def test_the_professor_named_on_the_second_page_is_not_a_divergent_name():
    item = activity(event_date=None, evidence_text="participou como membro da banca examinadora")
    first = "Participou como membro da banca examinadora do trabalho Estudo Ficticio sobre Dados."
    second = f"Assinaturas: {PROFESSOR}, Beltrano Silva."
    result = analyze([item], text_page(1, first), text_page(2, second), name="Beltrano Silva")
    assert DocAlertCode.DOCENTE_DIVERGENTE not in [a.code for a in result.alerts]
    assert result.status is DocumentStatus.PROCESSADO
