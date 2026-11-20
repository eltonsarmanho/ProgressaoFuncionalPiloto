"""Document type by keywords, which picks the extraction schema (EXT-09).

The text is normalized (lowercase, accent-free). The first matching rule wins: software
registration, defense minutes, declarations, certificates (Portuguese, then English), ordinances,
articles.
"""

import re

from app.domain.entities.extraction import DocumentType
from app.domain.rules.scoring_periods import normalize_title

_HEADER_CHARS = 300
_PORTARIA_HEADER_CHARS = 600

_BANCA = re.compile(r"membro da banca|banca examinadora|banca de ")
# the declaration says the professor took part in a board, or acted as advisor (REAL-20)
_BANCA_ROLE = re.compile(
    r"(?:participou|participacao|integrou|compos|presidiu)[^.]{0,80}banca|\bmembro d[ea] banca"
)
_ORIENTACAO_ROLE = re.compile(
    r"\b(?:e|foi|era|atua|atuou|atuando|exerce|exerceu)\s+(?:como\s+)?(?:co-?)?orientad(?:or|ora)\b"
    r"|\borientou\b|\bna condicao de (?:co-?)?orientad(?:or|ora)\b"
)
_ORIENTACAO = re.compile(r"\b(?:co-?)?orientad(?:or|ora)\b|\borientou\b")
_DECLARO = re.compile(r"\bdeclar(?:amos|o)\b")
_DISCIPLINAS = re.compile(r"componentes? curriculares?|\bch docente\b")
_ATA = re.compile(r"\bata\b")
_CERTIFICA = re.compile(r"\bcertificamos\b|\bcertifica que\b|\b(?:esse|este) certificado\b")
# English certificates (CER-01). The phrases are strong; the text layer may have lost the "ti"
# glyphs ("this is to cerfy"), so the verb is read by its first letters.
_CERTIFICA_EN = re.compile(
    r"\bthis is to cer\w{2,}|\bhereby cer\w{2,}"
    r"|\bcertificate of (?:participation|completion|attendance)\b"
)
# the bare word "certificate" counts only as a title line or as the last word of the text
_CERTIFICATE_LINE = re.compile(r"^\s*certificate\s*$", re.IGNORECASE | re.MULTILINE)
_PORTARIA_BODY = re.compile(r"\bresolve\b|\bdesignar\b|\bdesignado\b|\bdesigna\b|\bconsiderar\b")
_EVALUATION_FORM = re.compile(
    r"\b(?:ficha|formulario|folha)\s+de\s+avaliacao\b|\bavaliacao\s+d[oe]s?\s+seminarios?\b"
)
# strong markers; one of them plus a weak one, or two strong ones, make an article (REAL-19)
_ARTICLE_MARKERS = (
    re.compile(r"\bissn\b"),
    re.compile(r"\bdoi\b"),
    re.compile(r"\bresumo\b"),
    re.compile(r"\babstract\b"),
    re.compile(
        r"palavras[\s\-\u2013\u2014]*chave|\bkeywords?\b|\bindex terms\b|termos de indexacao"
    ),
)
_ARTICLE_WEAK_MARKERS = (
    re.compile(r"\bintroducao\b|\bintroduction\b"),
    re.compile(r"\breferencias\b|\breferences\b"),
)


def _is_article(norm: str) -> bool:
    strong = sum(1 for marker in _ARTICLE_MARKERS if marker.search(norm))
    weak = sum(1 for marker in _ARTICLE_WEAK_MARKERS if marker.search(norm))
    return strong >= 2 or (strong >= 1 and weak >= 1)


def _is_english_certificate(text: str, norm: str) -> bool:
    """English wording of a certificate; the bare word needs a text that is not an article."""
    if _CERTIFICA_EN.search(norm):
        return True
    bare = _CERTIFICATE_LINE.search(text) is not None or norm.endswith("certificate")
    return bare and not _is_article(norm)


def _declaration_type(text: str) -> DocumentType | None:
    declaration = _DECLARO.search(text)
    if declaration is None:
        return None
    body = text[declaration.start() :]
    if _DISCIPLINAS.search(body):
        return DocumentType.DECLARACAO_DISCIPLINAS
    banca_role, orientacao_role = _BANCA_ROLE.search(body), _ORIENTACAO_ROLE.search(body)
    if banca_role or orientacao_role:
        if banca_role and (orientacao_role is None or banca_role.start() < orientacao_role.start()):
            return DocumentType.DECLARACAO_BANCA
        return DocumentType.DECLARACAO_ORIENTACAO
    banca, orientacao = _BANCA.search(body), _ORIENTACAO.search(body)
    if banca and (orientacao is None or banca.start() < orientacao.start()):
        return DocumentType.DECLARACAO_BANCA
    if orientacao:
        return DocumentType.DECLARACAO_ORIENTACAO
    return None


def is_seminar_evaluation_form(text: str) -> bool:
    """A seminar evaluation form ("ficha de avaliação de seminário"): its evaluators are not a
    defense board, so it never counts as a banca (REAL-18)."""
    norm = normalize_title(text)
    return _EVALUATION_FORM.search(norm) is not None and "seminario" in norm


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
    if _is_english_certificate(text, norm):
        return DocumentType.CERTIFICADO
    if "portaria" in norm[:_PORTARIA_HEADER_CHARS] and _PORTARIA_BODY.search(norm):
        return DocumentType.PORTARIA
    return DocumentType.ARTIGO if _is_article(norm) else DocumentType.OUTRO
