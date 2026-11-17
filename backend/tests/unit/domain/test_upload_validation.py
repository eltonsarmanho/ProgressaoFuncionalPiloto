"""DOC-02, DOC-03, DOC-04 and the file name edge case: upload validation rules."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.domain.rules.upload_validation import (
    FileFacts,
    FileKind,
    UploadLimits,
    detect_kind,
    extension_of,
    safe_display_name,
    validate_upload,
)

MIB = 1024 * 1024
LIMITS = UploadLimits()

PDF = FileFacts(
    kind=FileKind.PDF,
    size_bytes=1000,
    page_count=3,
    megapixels=None,
    has_active_content=False,
    is_encrypted=False,
    is_readable=True,
)
JPEG = replace(PDF, kind=FileKind.JPEG, page_count=None, megapixels=Decimal("2.0"))
PNG = replace(PDF, kind=FileKind.PNG, page_count=None, megapixels=Decimal("2.0"))


def codes(rejections):
    return [r.code for r in rejections]


def test_default_limits_are_the_spec_values():
    assert LIMITS.max_file_bytes == 20 * MIB
    assert LIMITS.max_pages == 100
    assert LIMITS.max_megapixels == 100


@pytest.mark.parametrize(
    ("facts", "ext", "mime"),
    [
        (PDF, ".pdf", "application/pdf"),
        (JPEG, ".jpg", "image/jpeg"),
        (JPEG, ".jpeg", "image/jpeg"),
        (PNG, ".png", "image/png"),
        (PDF, ".PDF", "application/pdf"),
        (PDF, "pdf", "application/pdf; charset=binary"),
    ],
)
def test_allowed_files_pass(facts, ext, mime):
    assert validate_upload(facts, mime, ext, LIMITS) == []


@pytest.mark.parametrize("ext", [".exe", ".docx", ".txt", ""])
def test_other_extensions_are_refused_on_field_arquivo(ext):
    result = validate_upload(PDF, "application/pdf", ext, LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "EXTENSAO_INVALIDA")]


def test_pdf_extension_with_png_signature_is_refused():
    result = validate_upload(PNG, "application/pdf", ".pdf", LIMITS)
    assert [r.field for r in result] == ["arquivo"]
    assert codes(result) == ["ASSINATURA_DIVERGENTE"]


def test_unknown_signature_is_refused():
    unknown = replace(PDF, kind=FileKind.UNKNOWN)
    assert codes(validate_upload(unknown, "application/pdf", ".pdf", LIMITS)) == [
        "ASSINATURA_DIVERGENTE"
    ]


def test_declared_mime_not_matching_the_extension_is_refused():
    result = validate_upload(PDF, "image/png", ".pdf", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "MIME_DIVERGENTE")]


def test_mime_outside_the_allowed_list_is_refused():
    assert codes(validate_upload(PDF, "text/html", ".pdf", LIMITS)) == ["MIME_DIVERGENTE"]


@pytest.mark.parametrize("mime", ["application/octet-stream", None, ""])
def test_generic_or_missing_mime_passes_when_extension_and_signature_agree(mime):
    assert validate_upload(PDF, mime, ".pdf", LIMITS) == []


def test_generic_mime_does_not_rescue_a_wrong_signature():
    assert codes(validate_upload(PNG, "application/octet-stream", ".pdf", LIMITS)) == [
        "ASSINATURA_DIVERGENTE"
    ]


def test_exactly_20_mib_passes():
    facts = replace(PDF, size_bytes=20 * MIB)
    assert validate_upload(facts, "application/pdf", ".pdf", LIMITS) == []


def test_20_mib_plus_one_byte_is_refused():
    facts = replace(PDF, size_bytes=20 * MIB + 1)
    result = validate_upload(facts, "application/pdf", ".pdf", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "ARQUIVO_GRANDE")]


def test_100_pages_pass_and_101_are_refused():
    assert validate_upload(replace(PDF, page_count=100), "application/pdf", ".pdf", LIMITS) == []
    result = validate_upload(replace(PDF, page_count=101), "application/pdf", ".pdf", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "PAGINAS_EXCEDIDAS")]


def test_exactly_100_megapixels_pass_and_above_is_refused():
    ok = replace(JPEG, megapixels=Decimal("100"))
    assert validate_upload(ok, "image/jpeg", ".jpg", LIMITS) == []
    too_big = replace(JPEG, megapixels=Decimal("100.000001"))
    result = validate_upload(too_big, "image/jpeg", ".jpg", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "IMAGEM_GRANDE")]


def test_pdf_with_javascript_launch_or_embedded_file_is_refused_as_invalid():
    facts = replace(PDF, has_active_content=True)
    result = validate_upload(facts, "application/pdf", ".pdf", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "ARQUIVO_INVALIDO")]


def test_encrypted_pdf_is_refused_as_invalid():
    facts = replace(PDF, is_encrypted=True)
    result = validate_upload(facts, "application/pdf", ".pdf", LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "ARQUIVO_INVALIDO")]


@pytest.mark.parametrize("facts", [replace(PDF, page_count=None), replace(PNG, megapixels=None)])
def test_unreadable_file_is_refused_as_invalid(facts):
    unreadable = replace(facts, is_readable=False)
    mime = "application/pdf" if facts.kind is FileKind.PDF else "image/png"
    ext = ".pdf" if facts.kind is FileKind.PDF else ".png"
    result = validate_upload(unreadable, mime, ext, LIMITS)
    assert [(r.field, r.code) for r in result] == [("arquivo", "ARQUIVO_INVALIDO")]


def test_several_problems_are_all_reported():
    facts = replace(PDF, size_bytes=21 * MIB, page_count=101, is_encrypted=True)
    result = validate_upload(facts, "application/pdf", ".pdf", LIMITS)
    assert set(codes(result)) == {"ARQUIVO_GRANDE", "PAGINAS_EXCEDIDAS", "ARQUIVO_INVALIDO"}


def test_custom_limits_are_respected():
    small = UploadLimits(max_file_bytes=1000, max_pages=2, max_megapixels=1)
    assert codes(
        validate_upload(
            replace(PDF, size_bytes=1001, page_count=1), "application/pdf", ".pdf", small
        )
    ) == ["ARQUIVO_GRANDE"]
    assert codes(validate_upload(PDF, "application/pdf", ".pdf", small)) == ["PAGINAS_EXCEDIDAS"]


@pytest.mark.parametrize(
    ("first_bytes", "kind"),
    [
        (b"%PDF-1.7\n", FileKind.PDF),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", FileKind.JPEG),
        (b"\x89PNG\r\n\x1a\n\x00\x00", FileKind.PNG),
        (b"\x89PNG\r\n", FileKind.UNKNOWN),
        (b"PK\x03\x04", FileKind.UNKNOWN),
        (b"MZ\x90\x00", FileKind.UNKNOWN),
        (b" %PDF-1.7", FileKind.UNKNOWN),
        (b"", FileKind.UNKNOWN),
    ],
)
def test_detect_kind_reads_the_signature(first_bytes, kind):
    assert detect_kind(first_bytes) is kind


@pytest.mark.parametrize(
    ("name", "ext"),
    [
        ("declaracao.pdf", ".pdf"),
        ("Foto.JPEG", ".jpeg"),
        ("../../etc/passwd.png", ".png"),
        ("arquivo.tar.pdf", ".pdf"),
        ("semextensao", ""),
        ("pasta.pdf/arquivo", ""),
    ],
)
def test_extension_of_uses_the_last_suffix_of_the_base_name(name, ext):
    assert extension_of(name) == ext


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("declaracao.pdf", "declaracao.pdf"),
        ("../../etc/passwd", "passwd"),
        ("..\\..\\windows\\system32\\x.pdf", "x.pdf"),
        ("/abs/path/file.png", "file.png"),
        ("a\x00b.pdf", "ab.pdf"),
        ("..", "arquivo"),
        ("", "arquivo"),
    ],
)
def test_display_name_never_keeps_path_parts(name, shown):
    assert safe_display_name(name) == shown


def test_display_name_longer_than_255_is_cut_keeping_the_extension():
    shown = safe_display_name("a" * 400 + ".pdf")
    assert len(shown) == 255
    assert shown.endswith(".pdf")
    assert "/" not in safe_display_name("x/" * 300 + "y" * 300)
    assert len(safe_display_name("x/" * 300 + "y" * 300)) <= 255
