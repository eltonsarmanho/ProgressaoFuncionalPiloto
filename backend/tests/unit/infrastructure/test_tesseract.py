"""PIPE-06, PIPE-07, PIPE-08: Tesseract OCR in Portuguese with confidence and a time limit."""

import os
import stat
import time
from decimal import Decimal

import pytest
from PIL import Image

from app.domain.entities.document import DocAlertCode
from app.domain.rules.text_quality import ocr_needs_review
from app.infrastructure.ocr import tesseract
from app.infrastructure.ocr.render import load_image
from app.infrastructure.ocr.tesseract import OcrError, ocr_image, parse_tsv
from tests.support import synthetic_docs as docs

HEADER = "\t".join(
    "level page_num block_num par_num line_num word_num left top width height conf text".split()
)


def tsv_row(block, par, line, word, conf, text, level=5):
    return f"{level}\t1\t{block}\t{par}\t{line}\t{word}\t0\t0\t10\t10\t{conf}\t{text}"


def stub(tmp_path, body: str) -> str:
    path = tmp_path / "fake-tesseract"
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_synthetic_png_text_is_read_with_confidence_above_60(tmp_path):
    path = tmp_path / "doc.png"
    path.write_bytes(docs.png_with_text())
    result = ocr_image(load_image(path))
    text = result.text.lower()
    for word in ("banca", "examinadora", "fulana", "siape", "ficticio", "dados", "abertos"):
        assert word in text, word
    assert result.code is None
    assert result.confidence is not None and result.confidence > Decimal(60)
    assert ocr_needs_review(result.confidence, result.text) is False


def test_synthetic_jpg_text_is_read(tmp_path):
    path = tmp_path / "doc.jpg"
    path.write_bytes(docs.jpg_with_text())
    result = ocr_image(load_image(path))
    assert "banca" in result.text.lower()
    assert result.confidence is not None and result.confidence > Decimal(60)


def test_blank_image_gives_empty_text_and_no_confidence():
    result = ocr_image(Image.new("L", (800, 600), 255))
    assert result.text.strip() == ""
    assert result.confidence is None
    assert result.code is None
    assert ocr_needs_review(result.confidence, result.text) is True


def test_timeout_returns_the_code_and_kills_the_child_processes(tmp_path):
    pid_file = tmp_path / "pids"
    command = stub(tmp_path, f'echo $$ > "{pid_file}"\nsleep 30 &\necho $! >> "{pid_file}"\nwait\n')
    started = time.monotonic()
    result = ocr_image(Image.new("L", (50, 50), 255), timeout_seconds=1, tesseract_cmd=command)
    elapsed = time.monotonic() - started
    assert result.code is DocAlertCode.TEMPO_ESGOTADO
    assert result.text == ""
    assert result.confidence is None
    assert elapsed < 10
    pids = [int(p) for p in pid_file.read_text().split()]
    assert len(pids) == 2
    deadline = time.monotonic() + 3
    while any(alive(p) for p in pids) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert [alive(p) for p in pids] == [False, False]


def test_page_timeout_default_is_60_seconds():
    assert tesseract.PAGE_TIMEOUT_SECONDS == 60


def test_command_uses_portuguese_psm_3_tsv_nice_and_one_thread(tmp_path):
    args_file = tmp_path / "args"
    command = stub(
        tmp_path,
        f'echo "$@" > "{args_file}"\necho "$OMP_THREAD_LIMIT" >> "{args_file}"\n'
        f'echo "{HEADER}"\n',
    )
    ocr_image(Image.new("L", (10, 10), 255), tesseract_cmd=command)
    args, threads = args_file.read_text().splitlines()
    assert "stdout -l por --psm 3 tsv" in args
    assert args.split()[0].endswith(".png")
    assert threads == "1"


def test_temporary_image_is_removed(tmp_path):
    args_file = tmp_path / "args"
    command = stub(tmp_path, f'echo "$1" > "{args_file}"\necho "{HEADER}"\n')
    ocr_image(Image.new("L", (10, 10), 255), tesseract_cmd=command)
    used = args_file.read_text().strip()
    assert used.endswith("page.png")
    assert not os.path.exists(used)
    assert not os.path.exists(os.path.dirname(used))


def test_nonzero_exit_raises_ocr_error(tmp_path):
    command = stub(tmp_path, "exit 3\n")
    with pytest.raises(OcrError, match="status 3"):
        ocr_image(Image.new("L", (10, 10), 255), tesseract_cmd=command)


def test_missing_executable_raises_ocr_error():
    with pytest.raises(OcrError):
        ocr_image(Image.new("L", (10, 10), 255), tesseract_cmd="/nonexistent/tesseract-x")


def test_parse_joins_words_by_line_and_averages_confidence():
    tsv = "\n".join(
        [
            HEADER,
            tsv_row(0, 0, 0, 0, -1, "", level=1),
            tsv_row(1, 1, 1, 1, 90, "Declaramos"),
            tsv_row(1, 1, 1, 2, 80, "que"),
            tsv_row(1, 1, 2, 1, 70, "Maria"),
        ]
    )
    result = parse_tsv(tsv)
    assert result.text == "Declaramos que\nMaria"
    assert result.confidence == Decimal("80.00")


def test_parse_ignores_non_words_and_negative_confidence():
    tsv = "\n".join(
        [
            HEADER,
            tsv_row(1, 1, 1, 1, 95, "banca"),
            tsv_row(1, 1, 1, 2, -1, "lixo"),
            tsv_row(1, 1, 1, 3, 40, "   "),
            tsv_row(1, 1, 1, 0, 99, "linha", level=4),
        ]
    )
    result = parse_tsv(tsv)
    assert result.text == "banca"
    assert result.confidence == Decimal("95.00")


def test_parse_of_header_only_is_empty():
    result = parse_tsv(HEADER + "\n")
    assert result.text == ""
    assert result.confidence is None


def test_parse_keeps_a_word_with_a_quote():
    tsv = HEADER + "\n" + tsv_row(1, 1, 1, 1, 88, 'a"b')
    assert parse_tsv(tsv).text == 'a"b'
