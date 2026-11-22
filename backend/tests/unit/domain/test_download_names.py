"""VER-03: the download name is built by the server from the kind, interstice and version only."""

import re
from datetime import date

import pytest

from app.domain.entities.generated import DocumentFormat, DocumentKind
from app.domain.rules.download_names import download_name
from app.domain.rules.interstice import Interstice

INTERSTICE = Interstice(date(2020, 1, 1), date(2024, 12, 31))


@pytest.mark.parametrize(
    ("kind", "fmt", "expected"),
    [
        (DocumentKind.TABELA, DocumentFormat.PDF, "Tabela_de_Pontuacao_2020-2024_v2.pdf"),
        (DocumentKind.TABELA, DocumentFormat.DOCX, "Tabela_de_Pontuacao_2020-2024_v2.docx"),
        (DocumentKind.RELATORIO, DocumentFormat.PDF, "Relatorio_de_Atividades_2020-2024_v2.pdf"),
        (DocumentKind.RELATORIO, DocumentFormat.DOCX, "Relatorio_de_Atividades_2020-2024_v2.docx"),
        (
            DocumentKind.COMPROVANTE,
            DocumentFormat.PDF,
            "Comprovante_de_Documentos_2020-2024_v2.pdf",
        ),
        (
            DocumentKind.COMPROVANTE,
            DocumentFormat.DOCX,
            "Comprovante_de_Documentos_2020-2024_v2.docx",
        ),
        (DocumentKind.REQUERIMENTO, DocumentFormat.PDF, "Requerimento_2020-2024_v2.pdf"),
        (DocumentKind.REQUERIMENTO, DocumentFormat.DOCX, "Requerimento_2020-2024_v2.docx"),
        (DocumentKind.PARECER, DocumentFormat.PDF, "Parecer_2020-2024_v2.pdf"),
        (DocumentKind.PARECER, DocumentFormat.DOCX, "Parecer_2020-2024_v2.docx"),
    ],
)
def test_the_ten_names_follow_kind_interstice_and_version(kind, fmt, expected):
    assert download_name(kind, fmt, INTERSTICE, 2) == expected


@pytest.mark.parametrize("kind", list(DocumentKind))
@pytest.mark.parametrize("fmt", list(DocumentFormat))
def test_a_name_has_no_accent_no_space_and_only_safe_characters(kind, fmt):
    name = download_name(kind, fmt, INTERSTICE, 12)

    assert re.fullmatch(r"[A-Za-z0-9_.\-]+", name)


def test_the_name_carries_the_years_of_the_interstice_dates():
    interstice = Interstice(date(2022, 11, 23), date(2024, 11, 23))

    assert download_name(DocumentKind.TABELA, DocumentFormat.PDF, interstice, 1) == (
        "Tabela_de_Pontuacao_2022-2024_v1.pdf"
    )


def test_the_version_number_is_in_the_name():
    first = download_name(DocumentKind.TABELA, DocumentFormat.PDF, INTERSTICE, 1)
    tenth = download_name(DocumentKind.TABELA, DocumentFormat.PDF, INTERSTICE, 10)

    assert first.endswith("_v1.pdf")
    assert tenth.endswith("_v10.pdf")
