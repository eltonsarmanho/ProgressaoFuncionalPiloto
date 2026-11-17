"""ACC-01, ACC-02: pure parts of the local corpus script (no database, no network, no OCR)."""

import json
import stat
from datetime import date, datetime
from pathlib import Path

import pytest

from tests.support.corpus_script import load

corpus = load()
REPO_ROOT = Path(__file__).resolve().parents[3]

PERSONAL = "Joao Exemplo CPF 123.456.789-09 RG 1234567 SSP/PA joao.exemplo@ufpa.br (91) 98888-7777"


def test_mask_text_removes_cpf_rg_email_and_phone():
    masked = corpus.mask_text(PERSONAL)

    for fragment in ("123.456.789-09", "1234567", "joao.exemplo@ufpa.br", "98888-7777"):
        assert fragment not in masked
    assert masked.startswith("Joao Exemplo CPF [CPF] RG")
    assert "[EMAIL]" in masked and "[TELEFONE]" in masked


def test_mask_text_masks_bare_long_numbers_and_dotted_ids_but_keeps_dates_and_item_labels():
    masked = corpus.mask_text(
        "matricula 20240012345 identidade 12.345.678-9 em 2025-03-12 item III.4"
    )

    assert "20240012345" not in masked and "12.345.678-9" not in masked
    assert masked.endswith("em 2025-03-12 item III.4")


LONG_NAME = "Fulano da Silva Exemplo_2024001234567890123456789.pdf"


def test_mask_text_masks_a_long_digit_run_after_an_underscore():
    masked = corpus.mask_text(LONG_NAME)  # REAL-14: the digits after `_` are an identifier

    assert "2024001234567890123456789" not in masked
    assert not any(len(run) >= 11 for run in __import__("re").findall(r"\d+", masked))


def test_mask_text_masks_eleven_digits_but_keeps_ten_inside_a_word_and_dates():
    assert "12345678901" not in corpus.mask_text("arquivo_12345678901_x")
    assert corpus.mask_text("lote 2025-03-12 item III.4 ref ab1234567890cd") == (
        "lote 2025-03-12 item III.4 ref ab1234567890cd"
    )


def test_file_id_is_stable_hides_the_name_and_keeps_only_the_extension():
    first = corpus.file_id(LONG_NAME)

    assert first == corpus.file_id(LONG_NAME)
    assert first != corpus.file_id("Outro Nome.pdf")
    assert first.startswith("doc-") and first.endswith(".pdf")
    for fragment in ("Fulano", "Silva", "Exemplo", "2024"):
        assert fragment not in first
    assert corpus.file_id("a.PNG").endswith(".png")
    assert not any(char.isdigit() for char in first)


def test_file_id_differs_for_the_same_name_in_different_folders():
    assert corpus.file_id("Artigos/a.pdf") != corpus.file_id("Registros/a.pdf")


def test_mask_deep_masks_every_string_in_nested_structures():
    data = {"file": "CPF 123.456.789-09.pdf", "list": [{"x": "a@b.com"}], "n": 3}

    assert corpus.mask_deep(data) == {"file": "CPF [CPF].pdf", "list": [{"x": "[EMAIL]"}], "n": 3}


def test_load_env_file_reads_pairs_comments_export_and_quotes(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\nMARITALK_API_KEY='abc'\nexport MARITALK_API_BASE=\"https://x.test/v1\"\n"
        "MARITALK_MODEL=\n\nBROKEN\n",
        encoding="utf-8",
    )

    assert corpus.load_env_file(env) == {
        "MARITALK_API_KEY": "abc",
        "MARITALK_API_BASE": "https://x.test/v1",
        "MARITALK_MODEL": "",
    }
    assert corpus.load_env_file(tmp_path / "missing.env") == {}


def test_maritalk_model_falls_back_to_sabia_4_br_sp_when_empty_or_absent():
    assert corpus.maritalk_settings({"MARITALK_MODEL": ""})["maritalk_model"] == "sabia-4-br-sp"
    assert corpus.maritalk_settings({})["maritalk_model"] == "sabia-4-br-sp"
    assert corpus.maritalk_settings({"MARITALK_MODEL": "sabia-4-thinking"}) == {
        "maritalk_api_key": None,
        "maritalk_api_base": None,
        "maritalk_model": "sabia-4-thinking",
    }


def test_list_corpus_files_takes_supported_files_by_name_only(tmp_path):
    for name in ("b.PNG", "a.pdf", "c.jpeg", "notes.txt", ".hidden.pdf", "d.jpg"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "e.pdf").write_bytes(b"x")

    assert [p.name for p in corpus.list_corpus_files(tmp_path)] == [
        "a.pdf", "b.PNG", "c.jpeg", "d.jpg"
    ]


def test_list_corpus_files_recursive_takes_subfolders_in_path_order_and_skips_hidden(tmp_path):
    for relative in ("b.pdf", "Artigos/a.pdf", "Registros/x.png", "ATA Especializacao/y.pdf",
                     ".oculta/z.pdf", "Artigos/.rascunho.pdf", "Artigos/notas.txt"):  # fmt: skip
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")

    found = corpus.list_corpus_files(tmp_path, recursive=True)

    assert [p.relative_to(tmp_path).as_posix() for p in found] == [
        "Artigos/a.pdf", "ATA Especializacao/y.pdf", "b.pdf", "Registros/x.png",
    ]  # fmt: skip


def test_parser_is_recursive_by_default_and_no_recursive_turns_it_off():
    assert _parse().recursive is True
    assert _parse("--no-recursive").recursive is False
    assert _parse("--recursive").recursive is True


def test_repeated_no_item_alerts_count_once_and_keep_the_other_alerts():
    alerts, count = corpus.summarize_alerts(
        ["SEM_ITEM_DE_PONTUACAO", "TRUNCADO", "SEM_ITEM_DE_PONTUACAO", "SEM_ITEM_DE_PONTUACAO"]
    )

    assert alerts == ["SEM_ITEM_DE_PONTUACAO", "TRUNCADO"]
    assert count == 3


def test_alerts_without_no_item_are_untouched():
    assert corpus.summarize_alerts(["TRUNCADO", "TRUNCADO"]) == (["TRUNCADO", "TRUNCADO"], 0)


def test_item_label_uses_roman_group_and_is_none_without_item():
    assert corpus.item_label(8, 24) == "VIII.24"
    assert corpus.item_label(3, 4) == "III.4"
    assert corpus.item_label(None, None) is None
    assert corpus.item_label(3, None) is None


def test_interstice_summary_by_period_state():
    assert corpus.interstice_summary([]) == "SEM_ATIVIDADE"
    assert corpus.interstice_summary(["DENTRO", "DENTRO"]) == "DENTRO"
    assert corpus.interstice_summary(["FORA"]) == "FORA"
    assert corpus.interstice_summary(["DENTRO", "FORA"]) == "MISTO"


def _parse(*extra):
    return corpus.build_parser().parse_args(
        ["pasta", "--start", "2024-11-23", "--end", "2026-11-23", "--professor", "Fulana", *extra]
    )


def test_parser_reads_the_interstice_table_professor_and_optional_siape():
    args = _parse("--table", "Minha", "--siape", "1234567")

    assert (args.start, args.end) == (date(2024, 11, 23), date(2026, 11, 23))
    assert (args.professor, args.siape, args.table, args.dry_run) == (
        "Fulana", "1234567", "Minha", False
    )
    assert _parse().table is None and _parse().siape is None


def test_fake_ai_flag_is_an_alias_of_dry_run():
    assert _parse("--fake-ai").dry_run is True
    assert _parse("--dry-run").dry_run is True


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (["--siape", "123"], "SIAPE"),
        (["--limit", "0"], "--limit"),
    ],
)
def test_validate_args_refuses_bad_values(tmp_path, extra, message):
    args = corpus.build_parser().parse_args(
        [str(tmp_path), "--start", "2024-11-23", "--end", "2026-11-23", "--professor", "F", *extra]
    )

    with pytest.raises(corpus.CorpusError, match=message):
        corpus.validate_args(args)


def test_validate_args_refuses_end_not_after_start_and_missing_folder(tmp_path):
    base = ["--professor", "F"]
    backwards = corpus.build_parser().parse_args(
        [str(tmp_path), "--start", "2026-11-23", "--end", "2024-11-23", *base]
    )
    missing = corpus.build_parser().parse_args(
        [str(tmp_path / "nope"), "--start", "2024-11-23", "--end", "2026-11-23", *base]
    )

    with pytest.raises(corpus.CorpusError, match="posterior"):
        corpus.validate_args(backwards)
    with pytest.raises(corpus.CorpusError, match="pasta"):
        corpus.validate_args(missing)


def _entry(**changes):
    entry = corpus.DocumentEntry(
        file="Declaracao CPF 123.456.789-09.pdf",
        size_bytes=10,
        upload_status=201,
        status="PROCESSADO",
        document_type="DECLARACAO_BANCA",
        confidence="0.90",
        pages=2,
        page_methods=["TEXTO", "OCR"],
        items=["III.4"],
        interstice="DENTRO",
        activities=[
            corpus.ActivityEntry(
                item="III.4",
                status="AGUARDANDO_REVISAO",
                score_status="POTENCIAL",
                points="2",
                period="DENTRO",
                title="Banca de joao@ufpa.br",
            )
        ],
        grounding_warnings=[{"code": "NAO_ENCONTRADO_NO_TEXTO", "field": "hours",
                             "activity_index": 0}],
        alerts=["TRUNCADO"],
        wall_seconds=1.25,
    )
    for key, value in changes.items():
        setattr(entry, key, value)
    return entry


def _report(*documents):
    return corpus.CorpusReport(
        generated_at="2026-11-17T10:00:00-03:00",
        parameters={"start": "2024-11-23", "end": "2026-11-23", "ai": "dry-run (sem IA)"},
        process={
            "table": {"name": "Tabela de Pontuação da UFPA", "version": "Oficial"},
            "score": {
                "validated_total": "0",
                "potential_total": "2",
                "activities": 1,
                "pending": 1,
                "not_scored": 0,
                "alerts": [],
                "group_subtotals": {"III": "0"},
            },
            "documents": corpus.summarize_documents(documents),
            "elapsed_seconds": 3.0,
        },
        documents=list(documents),
    )


def test_report_json_masks_personal_data_in_every_string():
    data = _report(_entry()).to_dict()

    text = json.dumps(data, ensure_ascii=False)
    assert "123.456.789-09" not in text and "joao@ufpa.br" not in text
    # REAL-14: the file name is replaced by a stable id, so no name or number reaches the report
    assert data["documents"][0]["file"] == corpus.file_id("Declaracao CPF 123.456.789-09.pdf")
    assert "Declaracao" not in text


def test_report_dict_masks_long_digits_in_every_string_and_hides_the_file_name():
    entry = _entry(file=LONG_NAME, alerts=["ref_99999999999999"])

    text = json.dumps(_report(entry).to_dict(), ensure_ascii=False)

    assert corpus.file_id(LONG_NAME) in text
    assert "ref_[NUMERO]" in text
    for forbidden in ("Fulano", "Silva", "2024001234567890123456789", "99999999999999"):
        assert forbidden not in text


def test_markdown_report_lists_the_file_id_not_the_name():
    markdown = corpus.render_markdown(_report(_entry(file=LONG_NAME)).to_dict())

    assert corpus.file_id(LONG_NAME) in markdown
    assert "Fulano" not in markdown and "2024001234567890123456789" not in markdown


def test_markdown_lists_per_document_fields_and_per_process_potential_and_validated():
    data = _report(_entry()).to_dict()

    markdown = corpus.render_markdown(data)

    assert "123.456.789-09" not in markdown
    row = next(line for line in markdown.splitlines() if line.startswith("| 1 |"))
    for expected in (
        "DECLARACAO_BANCA", "PROCESSADO", "2 (TEXTO,OCR)", "III.4", "DENTRO", "0.90",
        "NAO_ENCONTRADO_NO_TEXTO:hours", "TRUNCADO", "1.2",
    ):
        assert expected in row
    assert "| Total validado | 0 |" in markdown
    assert "| Total potencial | 2 |" in markdown


def test_markdown_marks_document_without_scoring_item():
    entry = _entry(items=[], without_item=True, activities=[], interstice="SEM_ATIVIDADE")

    markdown = corpus.render_markdown(_report(entry).to_dict())

    row = next(line for line in markdown.splitlines() if line.startswith("| 1 |"))
    assert "SEM_ITEM_DE_PONTUACAO" in row


def test_write_report_creates_private_json_and_markdown_files(tmp_path):
    out_dir = tmp_path / "out" / "nested"

    json_path, md_path = corpus.write_report(
        _report(_entry()), out_dir, datetime(2026, 11, 17, 10, 5, 9)
    )

    assert json_path.name == "corpus-report-20261117-100509.json"
    assert md_path.name == "corpus-report-20261117-100509.md"
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["documents"][0]["status"] == "PROCESSADO"
    assert stat.S_IMODE(json_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(md_path.stat().st_mode) == 0o600


def test_real_documents_models_and_reports_are_git_ignored():
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    for entry in ("Documentos/", "Modelos/", "corpus-reports/"):
        assert entry in ignored
