"""The emblem of the UFPA that every generated document carries at the top (BRAS-06, BRAS-09).

The image is a PNG versioned inside the package (`assets/ufpa.png`), so the `COPY app ./app` of
the Dockerfile takes it to the image. A missing, empty or non-PNG file is a failure of the
generation (`EmblemUnavailable`), never a document without the emblem (BRAS-10). The error names
the file and never the path of the server.
"""

from pathlib import Path

from app.domain.rules.upload_validation import FileKind, detect_kind

EMBLEM_FILE = Path(__file__).parent / "assets" / "ufpa.png"
EMBLEM_WIDTH_MM = 20.0
EMBLEM_GAP_MM = 3.0

_IHDR_END = 24  # signature (8) + length and type of the IHDR (8) + width (4) + height (4)


class EmblemUnavailable(RuntimeError):
    """The file of the emblem does not exist, is empty or is not a PNG."""


def _header() -> bytes:
    try:
        head = EMBLEM_FILE.read_bytes()[:_IHDR_END]
    except OSError as error:
        raise EmblemUnavailable(
            f"Arquivo do brasão indisponível: {EMBLEM_FILE.name} não pôde ser lido"
        ) from error
    if detect_kind(head) is not FileKind.PNG or len(head) < _IHDR_END:
        raise EmblemUnavailable(
            f"Arquivo do brasão inválido: {EMBLEM_FILE.name} não é uma imagem PNG"
        )
    return head


def emblem_path() -> Path:
    """The file of the emblem, after checking that it is a PNG."""
    _header()
    return EMBLEM_FILE


def emblem_size_mm() -> tuple[float, float]:
    """Width of 20 mm and the height in proportion to the image, read from its header."""
    head = _header()
    pixels_wide = int.from_bytes(head[16:20], "big")
    pixels_high = int.from_bytes(head[20:24], "big")
    if pixels_wide == 0 or pixels_high == 0:
        raise EmblemUnavailable(f"Arquivo do brasão inválido: {EMBLEM_FILE.name} não tem tamanho")
    return EMBLEM_WIDTH_MM, EMBLEM_WIDTH_MM * pixels_high / pixels_wide
