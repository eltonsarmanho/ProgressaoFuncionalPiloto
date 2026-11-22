"""Download file names of the generated documents (VER-03).

Built from the kind, the interstice and the version only: never the professor's name, never an
accent or a space.
"""

from app.domain.entities.generated import DocumentFormat, DocumentKind
from app.domain.rules.interstice import Interstice

_STEMS = {
    DocumentKind.TABELA: "Tabela_de_Pontuacao",
    DocumentKind.RELATORIO: "Relatorio_de_Atividades",
    DocumentKind.COMPROVANTE: "Comprovante_de_Documentos",
    DocumentKind.REQUERIMENTO: "Requerimento",
    DocumentKind.PARECER: "Parecer",
}
_EXTENSIONS = {DocumentFormat.DOCX: "docx", DocumentFormat.PDF: "pdf"}


def download_name(
    kind: DocumentKind, fmt: DocumentFormat, interstice: Interstice, version: int
) -> str:
    """`Tabela_de_Pontuacao_2020-2024_v2.pdf`."""
    years = f"{interstice.start.year}-{interstice.end.year}"
    return f"{_STEMS[kind]}_{years}_v{version}.{_EXTENSIONS[fmt]}"
