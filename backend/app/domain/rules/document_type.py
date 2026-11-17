"""Document type by keywords, which picks the extraction schema (EXT-09).

The text is normalized (lowercase, accent-free). The first matching rule wins: software
registration, defense minutes, declarations, certificates, ordinances, articles.
"""

import re

from app.domain.entities.extraction import DocumentType
from app.domain.rules.scoring_periods import normalize_title

_HEADER_CHARS = 300
_PORTARIA_HEADER_CHARS = 600

_BANCA = re.compile(r"membro da banca|banca examinadora|banca de ")
_ORIENTACAO = re.compile(r"\b(?:co-?)?orientad(?:or|ora)\b|\borientou\b")
_DECLARO = re.compile(r"\bdeclar(?:amos|o)\b")
_DISCIPLINAS = re.compile(r"componentes? curriculares?|\bch docente\b")
_ATA = re.compile(r"\bata\b")
_CERTIFICA = re.compile(r"\bcertificamos\b|\bcertifica que\b|\b(?:esse|este) certificado\b")
_PORTARIA_BODY = re.compile(r"\bresolve\b|\bdesignar\b|\bdesignado\b|\bdesigna\b|\bconsiderar\b")
_ARTICLE_MARKERS = (
    re.compile(r"\bissn\b"),
    re.compile(r"\bdoi\b"),
    re.compile(r"\babstract\b|\bresumo\b"),
    re.compile(r"palavras-chave|\bkeywords?\b"),
)


def _declaration_type(text: str) -> DocumentType | None:
    declaration = _DECLARO.search(text)
    if declaration is None:
        return None
    body = text[declaration.start() :]
    if _DISCIPLINAS.search(body):
        return DocumentType.DECLARACAO_DISCIPLINAS
    banca, orientacao = _BANCA.search(body), _ORIENTACAO.search(body)
    if banca and (orientacao is None or banca.start() < orientacao.start()):
        return DocumentType.DECLARACAO_BANCA
    if orientacao:
        return DocumentType.DECLARACAO_ORIENTACAO
    return None


def detect_document_type(text: str) -> DocumentType:
    norm = normalize_title(text)
    if "instituto nacional da propriedade industrial" in norm and "programa de computador" in norm:
        return DocumentType.REGISTRO_SOFTWARE
    if (
        _ATA.search(norm[:_HEADER_CHARS])
        and "defesa" in norm
        and ("banca examinadora" in norm or "aprovad" in norm)
    ):
        return DocumentType.ATA_DEFESA
    declaration = _declaration_type(norm)
    if declaration is not None:
        return declaration
    if _CERTIFICA.search(norm) or re.search(r"\bcertificado\b", norm[:_HEADER_CHARS]):
        return DocumentType.CERTIFICADO
    if "portaria" in norm[:_PORTARIA_HEADER_CHARS] and _PORTARIA_BODY.search(norm):
        return DocumentType.PORTARIA
    if sum(1 for marker in _ARTICLE_MARKERS if marker.search(norm)) >= 2:
        return DocumentType.ARTIGO
    return DocumentType.OUTRO
