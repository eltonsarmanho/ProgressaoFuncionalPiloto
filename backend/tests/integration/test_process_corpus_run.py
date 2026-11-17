"""ACC-01, ACC-02: the corpus script on a synthetic folder, real PostgreSQL and a fake AI.

The documents are invented (tests.support.synthetic_docs); the real corpus is never read here.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.entities.extraction import DocumentType
from app.domain.repositories.ports import AiExtraction
from tests.support import synthetic_docs as synth
from tests.support.corpus_script import load
from tests.unit.application.analyzer_fakes import activity, payload

corpus = load()
OFFICIAL = "Tabela de Pontuação da UFPA"
EMPTY_TEXT = "Documento generico sem nenhuma atividade academica registrada para o docente."


class KeyedAi:
    """Answers a banca activity for the banca text and an empty list for any other text."""

    def __init__(self):
        self.calls = 0

    def extract(self, document_type: DocumentType, text: str) -> AiExtraction:
        self.calls += 1
        if "BANCA" in text:
            answer = payload(activity(), name=synth.FAKE_PROFESSOR)
        else:
            answer = payload(name=synth.FAKE_PROFESSOR, document_type="OUTRO")
        return AiExtraction(raw_json=answer, model="fake-model", duration_ms=1)


class InventingAi:
    """Returns hours that the page text does not contain (AD-009)."""

    def extract(self, document_type: DocumentType, text: str) -> AiExtraction:
        answer = payload(activity(hours=99), name=synth.FAKE_PROFESSOR)
        return AiExtraction(raw_json=answer, model="fake-model", duration_ms=1)


@pytest.fixture
def folder(tmp_path) -> Path:
    """a-banca.pdf (with a CPF in its text), b-outro.pdf, c-copia.pdf (same bytes as a)."""
    banca = synth.pdf_with_text(
        [synth.SAMPLE_PAGES[0] + f" Documento do declarante CPF {synth.FAKE_CPF}."]
    )
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a-banca.pdf").write_bytes(banca)
    (root / "b-outro.pdf").write_bytes(synth.pdf_with_text([EMPTY_TEXT]))
    (root / "c-copia.pdf").write_bytes(banca)
    (root / "leia-me.txt").write_text("not a document", encoding="utf-8")
    return root


def options(folder: Path, tmp_path: Path, **changes):
    values = {
        "folder": folder,
        "start": date(2024, 11, 23),
        "end": date(2026, 11, 23),
        "professor": synth.FAKE_PROFESSOR,
        "siape": synth.FAKE_SIAPE,
        "out_dir": tmp_path / "out",
        "env_file": None,
    }
    return corpus.Options(**(values | changes))


def run(folder, tmp_path, database_url, ai=None, **changes):
    return corpus.run_corpus(options(folder, tmp_path, **changes), database_url, ai_extractor=ai)


def by_name(report):
    return {d.file: d for d in report.documents}


def test_report_has_one_entry_per_supported_file_with_method_status_type_item_and_period(
    folder, tmp_path, engine, migrated_url
):
    report = run(folder, tmp_path, migrated_url, KeyedAi())

    docs = by_name(report)
    assert list(docs) == ["a-banca.pdf", "b-outro.pdf", "c-copia.pdf"]
    banca = docs["a-banca.pdf"]
    assert banca.page_methods == ["TEXTO"]
    assert banca.status == "PROCESSADO"
    assert banca.document_type == "DECLARACAO_BANCA"
    assert banca.items == ["III.4"]
    assert banca.interstice == "DENTRO"
    assert len(banca.activities) == 1
    assert banca.activities[0].status == "AGUARDANDO_REVISAO"
    assert banca.activities[0].title is None  # titles only with include_titles
    assert banca.wall_seconds is not None and banca.duration_ms is not None


def test_activity_outside_the_interstice_is_reported_as_outside(
    folder, tmp_path, engine, migrated_url
):
    report = run(
        folder, tmp_path, migrated_url, KeyedAi(), start=date(2022, 11, 23), end=date(2024, 11, 23)
    )

    assert by_name(report)["a-banca.pdf"].interstice == "FORA"
    assert by_name(report)["a-banca.pdf"].activities[0].period == "FORA"


def test_value_invented_by_the_ai_is_reported_as_a_grounding_warning(
    folder, tmp_path, engine, migrated_url
):
    banca = by_name(run(folder, tmp_path, migrated_url, InventingAi()))["a-banca.pdf"]

    assert banca.grounding_warnings == [
        {"code": "NAO_ENCONTRADO_NO_TEXTO", "field": "hours", "activity_index": 0}
    ]


def test_document_without_activity_is_listed_as_without_scoring_item(
    folder, tmp_path, engine, migrated_url
):
    other = by_name(run(folder, tmp_path, migrated_url, KeyedAi()))["b-outro.pdf"]

    assert other.status == "PROCESSADO"
    assert other.category == "SEM_ITEM_DE_PONTUACAO"
    assert other.without_item is True
    assert other.activities == [] and other.items == []
    assert other.alerts == ["NENHUMA_ATIVIDADE_ENCONTRADA"]
    assert other.interstice == "SEM_ATIVIDADE"


def test_duplicate_file_is_reported_with_the_conflict_status(
    folder, tmp_path, engine, migrated_url
):
    copy = by_name(run(folder, tmp_path, migrated_url, KeyedAi()))["c-copia.pdf"]

    assert copy.upload_status == 409
    assert copy.status is None


def test_process_score_summary_shows_potential_and_validated(
    folder, tmp_path, engine, migrated_url
):
    report = run(folder, tmp_path, migrated_url, KeyedAi())

    score = report.process["score"]
    assert report.process["table"]["name"] == OFFICIAL
    assert Decimal(score["potential_total"]) == 2  # III.4 is worth 2 points

    assert Decimal(score["validated_total"]) == 0
    assert score["pending"] == 1


def test_dry_run_skips_the_ai_and_still_reports_text_methods(
    folder, tmp_path, engine, migrated_url
):
    ai = KeyedAi()
    report = corpus.run_corpus(
        options(folder, tmp_path, dry_run=True), migrated_url, ai_extractor=None, env={}
    )

    banca = by_name(report)["a-banca.pdf"]
    assert ai.calls == 0
    assert banca.status == "EXTRAIDO_SEM_IA"
    assert banca.alerts == ["IA_INDISPONIVEL"]
    assert banca.page_methods == ["TEXTO"]
    assert banca.activities == []
    assert report.parameters["ai"] == "dry-run (sem IA)"


def test_report_carries_no_document_text_and_no_personal_data(
    folder, tmp_path, engine, migrated_url
):
    report = run(folder, tmp_path, migrated_url, KeyedAi())

    json_path, md_path = corpus.write_report(report, tmp_path / "out", datetime.now())
    for text in (json_path.read_text(encoding="utf-8"), md_path.read_text(encoding="utf-8")):
        for forbidden in (
            synth.FAKE_CPF,
            "Estudo Ficticio sobre Dados Abertos",
            synth.FAKE_PROFESSOR,
            "Faculdade Exemplo de Testes",
        ):
            assert forbidden not in text


def test_activity_titles_appear_only_when_asked_and_are_truncated(
    folder, tmp_path, engine, migrated_url
):
    titled = run(folder, tmp_path, migrated_url, KeyedAi(), include_titles=True)

    title = by_name(titled)["a-banca.pdf"].activities[0].title
    assert title == "Estudo Ficticio sobre Dados Abertos"
    assert len(title) <= corpus.MAX_TITLE_CHARS


def test_unknown_table_lists_the_available_ones(folder, tmp_path, engine, migrated_url):
    with pytest.raises(corpus.CorpusError, match=OFFICIAL):
        run(folder, tmp_path, migrated_url, KeyedAi(), table="Tabela inexistente")


def test_explicit_table_and_version_are_used(folder, tmp_path, engine, migrated_url):
    report = run(
        folder, tmp_path, migrated_url, KeyedAi(),
        table=OFFICIAL, table_version="Tabela oficial de pontuação UFPA",
    )

    assert report.process["table"] == {
        "name": OFFICIAL, "version": "Tabela oficial de pontuação UFPA"
    }


def test_real_ai_without_credentials_is_refused_before_any_work(
    folder, tmp_path, engine, migrated_url
):
    with pytest.raises(corpus.CorpusError, match="MARITALK_API_KEY"):
        corpus.run_corpus(options(folder, tmp_path), migrated_url, ai_extractor=None, env={})


def test_main_prints_only_counters_and_writes_the_reports(
    folder, tmp_path, engine, migrated_url, capsys, monkeypatch
):
    monkeypatch.setenv("MARITALK_API_KEY", "sk-test-secret-value")
    out_dir = tmp_path / "reports"

    code = corpus.main(
        [
            str(folder), "--start", "2024-11-23", "--end", "2026-11-23",
            "--professor", synth.FAKE_PROFESSOR, "--siape", synth.FAKE_SIAPE,
            "--database-url", migrated_url, "--out-dir", str(out_dir),
            "--env-file", str(tmp_path / "missing.env"), "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert code == 0
    assert "sk-test-secret-value" not in output
    assert synth.FAKE_PROFESSOR not in output and "Estudo Ficticio" not in output
    assert "Arquivos: 3" in output
    written = sorted(p.suffix for p in out_dir.iterdir())
    assert written == [".json", ".md"]
    report = json.loads(next(out_dir.glob("*.json")).read_text(encoding="utf-8"))
    assert "sk-test-secret-value" not in json.dumps(report)
