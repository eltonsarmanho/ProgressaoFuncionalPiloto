"""Upload validation: extension, MIME, signature, size, pages, pixels, active content.

DOC-02, DOC-03, DOC-04. Pure rules over facts the infrastructure inspector collects.
The original file name is display text only and never forms a path.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

MAX_NAME_LENGTH = 255
DEFAULT_NAME = "arquivo"


class FileKind(StrEnum):
    PDF = "PDF"
    JPEG = "JPEG"
    PNG = "PNG"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FileFacts:
    kind: FileKind
    size_bytes: int
    page_count: int | None
    megapixels: Decimal | None
    has_active_content: bool
    is_encrypted: bool
    is_readable: bool


@dataclass(frozen=True)
class UploadLimits:
    max_file_bytes: int = 20 * 1024 * 1024
    max_pages: int = 100
    max_megapixels: int = 100


@dataclass(frozen=True)
class Rejection:
    field: str
    code: str
    message: str


_KIND_BY_EXTENSION = {
    ".pdf": FileKind.PDF,
    ".jpg": FileKind.JPEG,
    ".jpeg": FileKind.JPEG,
    ".png": FileKind.PNG,
}
_MIME_BY_KIND = {
    FileKind.PDF: "application/pdf",
    FileKind.JPEG: "image/jpeg",
    FileKind.PNG: "image/png",
}
_GENERIC_MIME = {"", "application/octet-stream"}
_SIGNATURES = (
    (b"%PDF-", FileKind.PDF),
    (b"\xff\xd8\xff", FileKind.JPEG),
    (b"\x89PNG\r\n\x1a\n", FileKind.PNG),
)


def detect_kind(first_bytes: bytes) -> FileKind:
    """File kind from the signature (leading bytes), never from the name."""
    for signature, kind in _SIGNATURES:
        if first_bytes.startswith(signature):
            return kind
    return FileKind.UNKNOWN


def _base_name(name: str) -> str:
    return re.split(r"[/\\]", name)[-1]


def extension_of(name: str) -> str:
    """Lowercase last suffix of the base name, with the dot; empty when there is none."""
    base = _base_name(name)
    dot = base.rfind(".")
    return base[dot:].lower() if dot > 0 else ""


def safe_display_name(name: str) -> str:
    """Base name without path parts or control characters, at most 255 characters."""
    base = "".join(c for c in _base_name(name) if c.isprintable()).strip()
    if not base.strip("."):
        return DEFAULT_NAME
    if len(base) <= MAX_NAME_LENGTH:
        return base
    ext = extension_of(base)
    if len(ext) >= MAX_NAME_LENGTH:
        ext = ""
    return base[: MAX_NAME_LENGTH - len(ext)] + ext if ext else base[:MAX_NAME_LENGTH]


def _reject(code: str, message: str) -> Rejection:
    return Rejection(field="arquivo", code=code, message=message)


def validate_upload(
    facts: FileFacts,
    declared_mime: str | None,
    ext: str,
    limits: UploadLimits | None = None,
) -> list[Rejection]:
    """Rejections for one file; an empty list means the file is accepted."""
    limits = limits or UploadLimits()
    ext = ext.lower()
    ext = ext if ext.startswith(".") or not ext else "." + ext
    expected = _KIND_BY_EXTENSION.get(ext)
    if expected is None:
        return [_reject("EXTENSAO_INVALIDA", "Envie um arquivo PDF, JPG, JPEG ou PNG.")]
    if facts.kind is not expected:
        return [
            _reject("ASSINATURA_DIVERGENTE", "O conteúdo do arquivo não corresponde à extensão.")
        ]

    rejections: list[Rejection] = []
    mime = (declared_mime or "").split(";")[0].strip().lower()
    if mime not in _GENERIC_MIME and mime != _MIME_BY_KIND[expected]:
        rejections.append(
            _reject("MIME_DIVERGENTE", "O tipo declarado não corresponde ao arquivo.")
        )
    if facts.size_bytes > limits.max_file_bytes:
        rejections.append(_reject("ARQUIVO_GRANDE", "O arquivo passa do tamanho máximo."))
    if facts.page_count is not None and facts.page_count > limits.max_pages:
        rejections.append(_reject("PAGINAS_EXCEDIDAS", "O PDF passa do número máximo de páginas."))
    if facts.megapixels is not None and facts.megapixels > limits.max_megapixels:
        rejections.append(_reject("IMAGEM_GRANDE", "A imagem passa da resolução máxima."))
    if not facts.is_readable:
        rejections.append(_reject("ARQUIVO_INVALIDO", "O arquivo não pôde ser aberto."))
    if facts.is_encrypted:
        rejections.append(_reject("ARQUIVO_INVALIDO", "O arquivo está criptografado."))
    if facts.has_active_content:
        rejections.append(
            _reject("ARQUIVO_INVALIDO", "O PDF contém JavaScript, lançamento ou arquivo embutido.")
        )
    return rejections
