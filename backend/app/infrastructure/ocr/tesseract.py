"""Tesseract OCR by subprocess with TSV output (PIPE-06, PIPE-07, PIPE-08).

Portuguese, page segmentation 3, one thread, low priority (`nice`). The image goes to a
private temporary directory that is removed afterwards. A run past the time limit is killed
with its whole process group and reported as `TEMPO_ESGOTADO`.
"""

import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from PIL import Image

from app.domain.entities.document import DocAlertCode

PAGE_TIMEOUT_SECONDS = 60
LANGUAGE = "por"
PAGE_SEGMENTATION_MODE = "3"
NICENESS = "10"
_TSV_COLUMNS = 12
_WORD_LEVEL = "5"
_TWO_PLACES = Decimal("0.01")
_KILL_GRACE_SECONDS = 5


class OcrError(RuntimeError):
    """Tesseract is missing or exited with an error."""


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: Decimal | None  # mean word confidence, 0..100; None when there are no words
    code: DocAlertCode | None = None  # TEMPO_ESGOTADO when the time limit was exceeded


def parse_tsv(tsv: str) -> OcrResult:
    """Words of each line joined by spaces, lines by newlines; mean of confidences >= 0."""
    lines: dict[tuple[str, str, str], list[str]] = {}
    confidences: list[Decimal] = []
    for row in tsv.splitlines()[1:]:
        cells = row.split("\t", _TSV_COLUMNS - 1)
        if len(cells) < _TSV_COLUMNS or cells[0] != _WORD_LEVEL:
            continue
        word = cells[11].strip()
        try:
            confidence = Decimal(cells[10])
        except ArithmeticError:
            continue
        if not word or confidence < 0:
            continue
        lines.setdefault((cells[2], cells[3], cells[4]), []).append(word)
        confidences.append(confidence)
    text = "\n".join(" ".join(words) for words in lines.values())
    if not confidences:
        return OcrResult(text="", confidence=None)
    mean = sum(confidences) / len(confidences)
    return OcrResult(text=text, confidence=mean.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))


def _run(command: list[str], timeout: float) -> str | None:
    """Standard output of the command, or None after killing it on timeout."""
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
    except FileNotFoundError:
        raise OcrError("tesseract executable not found") from None
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        return None
    if process.returncode != 0:
        raise OcrError(f"tesseract exited with status {process.returncode}")
    return stdout.decode("utf-8", errors="replace")


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()


def ocr_image(
    image: Image.Image,
    timeout_seconds: float = PAGE_TIMEOUT_SECONDS,
    tesseract_cmd: str = "tesseract",
) -> OcrResult:
    """Text and mean confidence of a preprocessed image; `code` is set on timeout."""
    with tempfile.TemporaryDirectory(prefix="ocr-") as directory:
        picture = Path(directory) / "page.png"
        image.save(picture, format="PNG", compress_level=1)
        command = [
            "nice",
            "-n",
            NICENESS,
            tesseract_cmd,
            str(picture),
            "stdout",
            "-l",
            LANGUAGE,
            "--psm",
            PAGE_SEGMENTATION_MODE,
            "tsv",
        ]
        output = _run(command, timeout_seconds)
    if output is None:
        return OcrResult(text="", confidence=None, code=DocAlertCode.TEMPO_ESGOTADO)
    return parse_tsv(output)
