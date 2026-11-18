"""PIPE-02, DOC-01: document status transitions, alert codes and entities."""

from itertools import product
from uuid import uuid4

import pytest

from app.domain.entities.document import (
    DocAlertCode,
    Document,
    DocumentStatus,
    ExtractionRun,
    PageText,
    RunStatus,
    TextMethod,
    can_transition,
)

S = DocumentStatus
_FINAL = (S.PROCESSADO, S.REQUER_REVISAO, S.EXTRAIDO_SEM_IA, S.FALHOU)
_ALLOWED = {(S.PENDENTE, S.PROCESSANDO)}
_ALLOWED |= {(S.PROCESSANDO, final) for final in _FINAL}
_ALLOWED |= {(final, S.PENDENTE) for final in _FINAL}  # reprocessing / replacement: new run


def test_status_has_exactly_the_six_spec_values():
    assert {s.value for s in DocumentStatus} == {
        "PENDENTE",
        "PROCESSANDO",
        "PROCESSADO",
        "REQUER_REVISAO",
        "EXTRAIDO_SEM_IA",
        "FALHOU",
    }


def test_alert_codes_are_the_design_names_plus_those_of_the_real_validation():
    assert {c.value for c in DocAlertCode} == {
        "SEM_ITEM_DE_PONTUACAO",
        "TEXTO_ILEGIVEL",
        "DOCENTE_DIVERGENTE",
        "RESPOSTA_INVALIDA",
        "NAO_ENCONTRADO_NO_TEXTO",
        "TRUNCADO",
        "NENHUMA_ATIVIDADE_ENCONTRADA",
        "IA_CREDENCIAL_RECUSADA",
        "IA_INDISPONIVEL",
        "TEMPO_ESGOTADO",
        "QUANTIDADE_ESTIMADA",
        "ATIVIDADE_REPETIDA",  # REAL-07
        "CLAUSULA_DE_DISPENSA",  # REAL-10
        "TENTATIVAS_ESGOTADAS",  # VER-04
        "DATA_PARCIAL",  # VER-10
        "DATA_FIM_DERIVADA",  # SEG-01
        "DATA_FIM_AUSENTE",  # SEG-02
        "INDEXACAO_NAO_COMPROVADA",  # TER-06
    }
    assert len(DocAlertCode) == 18


def test_pending_goes_to_processing():
    assert can_transition(S.PENDENTE, S.PROCESSANDO) is True


@pytest.mark.parametrize("final", _FINAL)
def test_processing_goes_to_each_final_status(final):
    assert can_transition(S.PROCESSANDO, final) is True


@pytest.mark.parametrize("final", _FINAL)
def test_final_status_goes_back_to_pending_for_a_new_run(final):
    assert can_transition(final, S.PENDENTE) is True


def test_pending_cannot_skip_processing():
    for final in _FINAL:
        assert can_transition(S.PENDENTE, final) is False


@pytest.mark.parametrize(
    ("current", "target"),
    [pair for pair in product(DocumentStatus, DocumentStatus) if pair not in _ALLOWED],
)
def test_every_other_transition_is_refused(current, target):
    assert can_transition(current, target) is False


def test_processing_cannot_return_to_pending_or_stay():
    assert can_transition(S.PROCESSANDO, S.PENDENTE) is False
    assert can_transition(S.PROCESSANDO, S.PROCESSANDO) is False


def test_final_statuses_cannot_move_to_another_final_status():
    for a, b in product(_FINAL, _FINAL):
        assert can_transition(a, b) is False


def test_new_document_is_pending_with_version_one():
    doc = Document(
        id=uuid4(),
        process_id=uuid4(),
        original_name="declaracao.pdf",
        internal_name="a1b2.pdf",
        mime="application/pdf",
        size_bytes=1024,
        sha256="0" * 64,
        page_count=2,
        uploaded_by=uuid4(),
    )
    assert doc.status is DocumentStatus.PENDENTE
    assert doc.version == 1
    assert doc.status_code is None
    assert doc.suggested_type is None
    assert doc.manual_type is None
    assert doc.confidence is None


def test_page_text_keeps_method_confidence_and_text():
    page = PageText(
        document_id=uuid4(),
        run_id=uuid4(),
        page_number=1,
        method=TextMethod.OCR,
        char_count=5,
        ocr_confidence=None,
        text="abcde",
    )
    assert page.method.value == "OCR"
    assert {m.value for m in TextMethod} == {"TEXTO", "OCR"}
    assert page.text == "abcde"


def test_extraction_run_status_is_active_or_replaced():
    assert {s.value for s in RunStatus} == {"ATIVA", "SUBSTITUIDA"}
    run = ExtractionRun(
        id=uuid4(), document_id=uuid4(), model="sabia-4-br-sp", duration_ms=1200, raw_json={}
    )
    assert run.status is RunStatus.ATIVA
    assert run.warnings == ()
