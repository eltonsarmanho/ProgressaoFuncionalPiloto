"""Taxonomy to scoring item rules, numbered as in the official UFPA table (CLS-02..04, MAP)."""

import re
from dataclasses import dataclass

from app.domain.entities.activity import Level
from app.domain.entities.extraction import DocumentType
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.document_type import is_seminar_evaluation_form
from app.domain.rules.grounding import professor_named_in_text
from app.domain.rules.scoring_periods import normalize_title

_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
_SOURCE = "Tabela oficial de pontuação da UFPA"
_NO_ITEM_TAXONOMY = "Decisão do usuário em 2026-11-17: coorientação de TCC de graduação não pontua"
_NO_ITEM_OTHER = "Tipo sem item na tabela oficial de pontuação da UFPA"


@dataclass(frozen=True)
class Item:
    group: int
    item: int


@dataclass(frozen=True)
class Suggestion:
    principal: Item | None
    alternatives: tuple[Item, ...]
    source_note: str


def _note(item: Item) -> str:
    return f"{_SOURCE}, Grupo {_ROMAN[item.group]}, item {item.item}"


def _rule(group: int, number: int, *alternatives: tuple[int, int]) -> Suggestion:
    principal = Item(group, number)
    return Suggestion(principal, tuple(Item(g, n) for g, n in alternatives), _note(principal))


_RULES: dict[T, Suggestion] = {
    T.ORIENTACAO_POS_DOUTORADO: _rule(2, 1),
    T.ORIENTACAO_DOUTORADO: _rule(2, 2),
    T.COORIENTACAO_DOUTORADO: _rule(2, 4),
    T.ORIENTACAO_MESTRADO: _rule(2, 3),
    T.COORIENTACAO_MESTRADO: _rule(2, 5),
    T.ORIENTACAO_ESPECIALIZACAO: _rule(2, 6),
    T.ORIENTACAO_TCC_GRADUACAO: _rule(2, 7),
    T.COORIENTACAO_TCC_GRADUACAO: Suggestion(None, (), _NO_ITEM_TAXONOMY),
    T.ORIENTACAO_EM_ANDAMENTO_DOUTORADO: _rule(2, 14),
    T.ORIENTACAO_EM_ANDAMENTO_MESTRADO: _rule(2, 15),
    T.ORIENTACAO_EM_ANDAMENTO_TCC: _rule(2, 16),
    T.ORIENTACAO_PROJETO_INSTITUCIONAL: _rule(2, 8, (2, 9)),
    T.ORIENTACAO_ESTAGIO: _rule(2, 12),
    T.ORIENTACAO_MONITORIA: _rule(2, 13),
    T.BANCA_DOUTORADO: _rule(3, 1),
    T.BANCA_MESTRADO: _rule(3, 2),
    T.BANCA_ESPECIALIZACAO: _rule(3, 3),
    T.BANCA_TCC_GRADUACAO: _rule(3, 4),
    T.BANCA_CONCURSO_SUBSTITUTO: _rule(3, 5),
    T.BANCA_CONCURSO_EFETIVO: _rule(3, 6),
    T.BANCA_QUALIFICACAO: _rule(3, 7),
    T.BANCA_SELECAO_POS: _rule(3, 8),
    T.BANCA_SELECAO_BOLSAS: _rule(3, 9),
    T.BANCA_PROCESSO_SELETIVO: Suggestion(None, (), _NO_ITEM_OTHER),
    T.EXTENSAO_PROJETO_COORDENACAO: _rule(4, 1),
    T.EXTENSAO_PROJETO_PARTICIPACAO: _rule(4, 2),
    T.EXTENSAO_CURSO_COORDENACAO: _rule(4, 3),
    T.EXTENSAO_CURSO_MINISTRANTE: _rule(4, 4, (4, 5)),
    T.EXTENSAO_EVENTO_COORDENACAO: _rule(4, 6),
    T.EXTENSAO_EVENTO_MINISTRANTE: Suggestion(None, (), _NO_ITEM_OTHER),
    T.PESQUISA_PROJETO_COORDENACAO: _rule(5, 1),
    T.PESQUISA_GRUPO_COORDENACAO: _rule(5, 2),
    T.PESQUISA_GRUPO_MEMBRO: _rule(5, 3),
    T.PESQUISA_BOLSA_PRODUTIVIDADE: _rule(5, 4),
    T.FUNCAO_DIRETOR_FACULDADE: _rule(6, 6, (6, 3)),
    T.FUNCAO_VICE_DIRETOR_FACULDADE: _rule(6, 7),
    T.FUNCAO_COORDENADOR_CURSO_GRADUACAO: _rule(6, 7),
    T.COMISSAO_ADMINISTRACAO_SUPERIOR: _rule(6, 10, (6, 14)),
    T.COMISSAO_NDE_MEMBRO: _rule(6, 10, (6, 14)),
    T.COMISSAO_UNIDADE: _rule(6, 12, (6, 14)),
    T.COLEGIADO_MEMBRO: _rule(6, 13),
    T.CURSO_ESPECIALIZACAO_CONCLUIDO: _rule(7, 7),
    T.CURSO_APERFEICOAMENTO_CONCLUIDO: _rule(7, 8, (7, 9)),
    T.CURSO_EXTENSAO_CONCLUIDO: _rule(7, 9),
    T.CURSO_CONCLUIDO: _rule(7, 10),
    T.PARTICIPACAO_EVENTO: _rule(7, 10),
    T.TREINAMENTO_INTERNO: _rule(7, 10),
    T.ESTAGIO_CAPACITACAO: _rule(7, 11),
    T.LIVRO_COM_PARECERISTAS: _rule(8, 1),
    T.LIVRO_SEM_PARECERISTAS: _rule(8, 2),
    T.CAPITULO_INTERNACIONAL: _rule(8, 3),
    T.CAPITULO_NACIONAL: _rule(8, 4),
    T.ARTIGO_INTERNACIONAL_INDEXADO: _rule(8, 9, (8, 11)),
    T.ARTIGO_NACIONAL_INDEXADO: _rule(8, 10, (8, 11)),
    T.ARTIGO_NAO_INDEXADO: _rule(8, 11),
    T.TRABALHO_COMPLETO_CONGRESSO: _rule(8, 19, (8, 10)),
    T.COMUNICACAO_COM_RESUMO: _rule(8, 20),
    T.COMUNICACAO_SEM_RESUMO: _rule(8, 21),
    T.APRESENTACAO_TRABALHO_INTERNACIONAL: _rule(8, 22),
    T.APRESENTACAO_TRABALHO_NACIONAL: _rule(8, 23),
    T.PALESTRA: _rule(8, 24),
    T.PATENTE_DEPOSITADA: _rule(8, 29),
    T.PATENTE_CONCEDIDA: _rule(8, 30),
    T.REGISTRO_SOFTWARE: _rule(8, 33),
    T.CONSULTORIA_AD_HOC: _rule(8, 36),
    T.OUTRA: Suggestion(None, (), _NO_ITEM_OTHER),
}


def suggest_item(taxonomy: T, level: Level | None = None) -> Suggestion:
    """Item suggested for a taxonomy code; the level only matters for the classes of Group I.

    With an unknown level, the discipline gets I.1 and keeps I.2 as the alternative.
    """
    if taxonomy is T.DISCIPLINA_MINISTRADA:
        if level is Level.POS_GRADUACAO:
            return _rule(1, 2)
        if level is Level.GRADUACAO:
            return _rule(1, 1)
        return _rule(1, 1, (1, 2))
    return _RULES[taxonomy]


# "extensão" inside the name of an institutional unit says who issued the document, not what
# the course is: "Pró-Reitoria de Extensão", "Coordenadoria de Extensão", "PROEX".
_EXTENSION_UNIT = re.compile(
    r"\b(?:pro[- ]?reit\w+|diretoria|coordenadoria|coordenacao|centro|nucleo|secretaria|"
    r"departamento|setor|assessoria|divisao|gerencia|superintendencia)"
    r"\s+(?:adjunta\s+)?(?:de|da|do)\s+extensao\b|\bproex\b"
)
_EXTENSION_NATURE = re.compile(
    r"\b(?:cursos?|minicursos?|atividades?|acao|acoes|programas?|projetos?|eventos?|oficinas?)"
    r"\s+(?:de|em)\s+extensao\b"
    r"|\bextensao\s+universitaria\b"
    r"|\b(?:categoria|natureza|tipo|modalidade|classificacao)(?:\s+d[aeo]s?\s+\w+)?\s*[:\-]?\s*"
    r"extensao\b"
)


def confirm_extension_course(taxonomy: T, text: str) -> T:
    """A course counts as extension only when "extensão" names its nature (CLS-10, SEG-06).

    Accepted: "curso/atividade/ação/programa/projeto/evento de extensão" and a category field
    ("Categoria: Extensão"). The word inside the name of a unit ("Pró-Reitoria de Extensão",
    "PROEX") or in a list of missions does not count; the course is then a training (VII.10).
    """
    if taxonomy is not T.CURSO_EXTENSAO_CONCLUIDO:
        return taxonomy
    body = _EXTENSION_UNIT.sub(" ", normalize_title(text))
    return taxonomy if _EXTENSION_NATURE.search(body) else T.CURSO_CONCLUIDO


def confirm_board_document(taxonomy: T, document_type: DocumentType, text: str) -> T:
    """Only defense minutes, board declarations and the like make a banca (REAL-18).

    A seminar evaluation form that no rule recognizes (type OUTRO) can list evaluators and
    grades; the AI takes them for a master's board. Such a banca has no scoring item.
    """
    is_board = taxonomy.value.startswith("BANCA_")
    if is_board and document_type is DocumentType.OUTRO and is_seminar_evaluation_form(text):
        return T.OUTRA
    return taxonomy


_EXTENSION_PROJECTS = frozenset({T.EXTENSAO_PROJETO_COORDENACAO, T.EXTENSAO_PROJETO_PARTICIPACAO})
_PAPIM_WORDING = re.compile(r"\bpapim\b|intervencao metodologica")


def confirm_extension_project(taxonomy: T, text: str) -> T:
    """A project or program counts as extension only when the document says so (REAL-12).

    The accepted wording is "extensão"; for the coordination item IV.1 also the table's own
    ("PAPIM", "intervenção metodológica"), which only that item names in the official table
    (SEG-09). Without it the activity has no scoring item (`OUTRA`): the human review decides,
    and no IV.1 or IV.2 points are suggested for a project that may be research.
    """
    if taxonomy not in _EXTENSION_PROJECTS:
        return taxonomy
    normalized = normalize_title(text)
    if "extensao" in normalized:
        return taxonomy
    if taxonomy is T.EXTENSAO_PROJETO_COORDENACAO and _PAPIM_WORDING.search(normalized):
        return taxonomy
    return T.OUTRA


_RESEARCH_COORDINATION = frozenset({T.PESQUISA_PROJETO_COORDENACAO, T.PESQUISA_GRUPO_COORDENACAO})
_TITLE_ABBREVIATION = re.compile(r"\b(prof\w*|dra?|sra?|ma|ms)\.", re.IGNORECASE)
_COORDINATOR = re.compile(r"\b(?:coordena\w*|lider(?:es)?|lideranca)\b")
_COORDINATED_BY = re.compile(r"\bcoordenad[oa]s?\s+(?:pel[oa]s?|por)\b")
_RESEARCH_WORDS = re.compile(r"\b(?:pesquisa|projeto|grupo)\b")


def confirm_research_coordination(taxonomy: T, text: str, professor_name: str) -> T:
    """Coordination of a research project or group needs the role in the text (SEG-07).

    One sentence must name the professor and a coordination word ("coordenadora", "coordena",
    "líder"), and the document must speak of a research project or group. "Coordenado por
    Fulano" does not make the professor the coordinator. A participation certificate that the
    AI took for coordination has no scoring item (`OUTRA`): the human review decides.
    """
    if taxonomy not in _RESEARCH_COORDINATION:
        return taxonomy
    if not _RESEARCH_WORDS.search(normalize_title(text)):
        return T.OUTRA
    for sentence in re.split(r"[.;\n]+", _TITLE_ABBREVIATION.sub(r"\1", text)):
        role = _COORDINATED_BY.sub(" ", normalize_title(sentence))
        if _COORDINATOR.search(role) and professor_named_in_text(professor_name, sentence):
            return taxonomy
    return T.OUTRA


_DISMISSAL_TAXONOMIES = frozenset(
    {
        T.FUNCAO_DIRETOR_FACULDADE,
        T.FUNCAO_VICE_DIRETOR_FACULDADE,
        T.FUNCAO_COORDENADOR_CURSO_GRADUACAO,
        T.COMISSAO_ADMINISTRACAO_SUPERIOR,
        T.COMISSAO_NDE_MEMBRO,
        T.COMISSAO_UNIDADE,
        T.COLEGIADO_MEMBRO,
    }
)
_VOIDED = re.compile(r"\bsem efeito\b")  # "fica sem efeito a designação ..."
_DISMISSAL = re.compile(r"\bdispens\w*|\bexoner\w*|\bdestitu\w*|\bcessa\w*")
_DESIGNATION = re.compile(
    r"\bdesign\w*|\bnomea\w*|\bnomead\w*|\brecondu\w*|\bempossa\w*|\binvest\w*"
)


def is_dismissal_clause(taxonomy: T, evidence_text: str) -> bool:
    """A portaria clause that dispenses the professor from a function is not an activity.

    Only the designation scores (REAL-10). The clause is a dismissal when its quoted passage
    says so and does not also designate; a passage with both is kept for the human review.
    """
    if taxonomy not in _DISMISSAL_TAXONOMIES:
        return False
    passage = normalize_title(evidence_text)
    if _VOIDED.search(passage):
        return True
    return _DISMISSAL.search(passage) is not None and _DESIGNATION.search(passage) is None
