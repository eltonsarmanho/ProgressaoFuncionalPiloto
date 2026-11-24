"""OFI-02..OFI-06: every item of the official table pinned against the spreadsheet.

The expected values below were written from `Modelos/tabela-progressao-docente.xlsx`
(cell formulas, not the seed), with the five decisions of the user applied: II.10 = 10,
VI.14 = 3 (GI-12, decision of 2026-11-19), VIII.4 = 15, VIII.8 = 15, VIII.12 = 2. Each row is
`(item, points, unit label, start of the description, end of the description)`; texts are
whitespace-normalized and the numbering prefix is dropped. The sums per group are not enough:
two compensating errors (II.1 <-> II.2) keep them intact.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[2] / "app/infrastructure/database/seed_data"

GROUP_II = [
    (1, 20, "por aluno", "Tutoria de pós-doutorado", "ída (20 pontos por aluno)"),
    (2, 30, "por aluno", "Orientação de tese de dou", "da (30 pontos por aluno)."),
    (3, 15, "por aluno", "Orientação de dissertação", "da (15 pontos por aluno)."),
    (4, 15, "por aluno", "Co-orientação de tese de", "da (15 pontos por aluno)."),
    (5, 8, "por aluno", "Co-orientação de disserta", "ida (8 pontos por aluno)."),
    (6, 8, "por aluno", "Orientação de monografia", "ída (8 pontos por aluno)."),
    (7, 5, "por aluno", "Orientação de trabalho de", "ido (5 pontos por aluno)."),
    (8, 3, "por aluno", "Orientação de aluno em pr", "são (3 pontos por aluno)."),
    (9, 2, "por aluno", "Orientação de aluno em pr", "ico (2 pontos por aluno)."),
    (10, 10, "por ano de exercício", "Tutorial de Grupo PET e d", "os por ano de exercício)."),
    (11, 2, "por ano", "Orientação de aluno do Gr", "o PET (2 pontos por ano)."),
    (12, 5, "por aluno/ano", "Orientação de aluno em es", "(5 pontos por aluno/ano)."),
    (13, 5, "por aluno", "Orientação de aluno em pr", "ria (5 pontos por aluno)."),
    (14, 15, "por aluno", "Orientação de tese de dou", "o (15 pontos por aluno )."),
    (15, 10, "por aluno", "Orientação de dissertação", "o (10 pontos por aluno )."),
    (16, 5, "por aluno", "Orientação de trabalho de", "ento (5 pontos por aluno)"),
]

GROUP_III = [
    (1, 10, "por banca", "Membro de banca examinado", "o (10 pontos por banca )."),
    (2, 5, "por banca", "Membro de banca examinado", "do (5 pontos por banca )."),
    (3, 2, "por banca", "Membro da banca examinado", "ada (2 pontos por banca)."),
    (4, 2, "por banca", "Membro de banca examinado", "ico (2 pontos por banca)."),
    (5, 5, "por banca", "Membro de banca de concur", "to (5 pontos por banca )."),
    (6, 10, "por banca", "Membro de banca de concur", "o (10 pontos por banca )."),
    (7, 5, "por banca", "Membro de banca de qualif", "ão (5 pontos por banca )."),
    (8, 3, "por banca", "Membro de banca de seleçã", "ão (3 pontos por banca )."),
    (9, 2, "por banca", "Membro de banca de seleçã", "is (2 pontos por banca )."),
]

GROUP_IV = [
    (1, 15, "por ação", "Coordenação e execução de", "oal concedido ao docente."),
    (2, 8, "por ação", "Participação em Programas", "o registrados (8 pontos)."),
    (3, 8, "por ação", "Coordenação de curso de e", "o ano/período (8 pontos)."),
    (4, 2, "por ação", "Ministrante de curso de e", "o ano/período (2 pontos)."),
    (5, 2, "por ação", "Ministrante de curso de a", "ínimo de 20 h (2 pontos)."),
    (6, 5, "por ação", "Coordenação de evento de", "o ano/período (5 pontos)."),
]

GROUP_V = [
    (1, 20, "por ano de exercício", "Coordenação e execução de", "os por ano de exercício)."),
    (2, 15, "por ano de exercício", "Coordenação de grupo de p", "os por ano de exercício)."),
    (3, 10, "por ano de exercício", "Membro do grupo de pesqui", "os por ano de exercício)."),
    (4, 15, "por ano de obtenção", "Bolsa de produtividade em", "tos por ano de obtenção)."),
    (5, 15, "por ano de exercício", "Coordenação de núcleo de", "os por ano de exercício)."),
]

GROUP_VI = [
    (1, 70, "por ano de exercício", "Reitor e Vice-Reitor (70", "os por ano de exercício)."),
    (2, 50, "por ano de exercício", "Pró-Reitor (50 pontos por", "os por ano de exercício)."),
    (3, 50, "por ano de exercício", "Coordenador de Campus (po", "os por ano de exercício)."),
    (4, 40, "por ano de exercício", "Vice- Coordenador de Camp", "os por ano de exercício)."),
    (5, 25, "por ano de exercício", "Presidente de Comissão de", "os por ano de exercício)."),
    (6, 30, "por ano de exercício", "Diretor de Faculdade/Esco", "os por ano de exercício)."),
    (7, 20, "por ano de exercício", "Vice-Diretor de Faculdade", "os por ano de exercício)."),
    (8, 10, "por ano", "Coordenador de Projetos d", "UFPA (10 pontos por ano)."),
    (9, 10, "por ano de exercício", "Coordenador de Curso de E", "os por ano de exercício)."),
    (10, 5, "por ano de exercício", "Membro de Comissão consti", "tos por ano de exercício)"),
    (11, 8, "por ano de exercício", "Membro de Comitê Editoria", "os por ano de exercício)."),
    (12, 3, "por ano de exercício", "Vice-Coordenador de Curso", "pósio, jornada, encontro."),
    (13, 5, "por ano de exercício", "Membro titular ou suplent", "os por ano de exercício)."),
    (14, 3, "por ano", "Membro titular ou suplent", "ões. ( 3 pontos por ano)."),
]

GROUP_VII = [
    (1, 90, "no interstício", "Doutor ou livre-docente.", "90 pontos no interstício)"),
    (2, 60, "no interstício", "Mestre. (60 pontos no int", "60 pontos no interstício)"),
    (3, 30, "no interstício", "Pós-doutorado (realizado", "30 pontos no interstício)"),
    (4, 15, "no interstício", "Estágio de pós-doutorado", "15 pontos no interstício)"),
    (5, 20, "no interstício", "Créditos de doutorado (co", "20 pontos no interstício)"),
    (6, 20, "no interstício", "Créditos de mestrado (con", "20 pontos no interstício)"),
    (7, 10, "no interstício", "Curso de especialização (", "10 pontos no interstício)"),
    (8, 5, "no interstício", "Curso de aperfeiçoamento", "5 pontos no interstício)"),
    (9, 5, "no interstício", "Curso de extensão com fre", "(5 pontos no interstício)"),
    (10, 2, "no interstício", "Participação em congresso", "(2 pontos no interstício)"),
    (11, 1, "a cada 30 horas", "Estágio de capacitação té", "cada 30 horas = 1 ponto)."),
]

GROUP_VIII = [
    (1, 50, "por unidade", "Autor de livro publicado", "pareceristas. (50 pontos)"),
    (2, 20, "por unidade", "Autor de livro publicado", "pareceristas. (20 pontos)"),
    (3, 20, "por unidade", "Autor de capítulo publica", "nternacional. (20 pontos)"),
    (4, 15, "por unidade", "Autor de capítulo publica", "ora nacional. (15 pontos)"),
    (5, 20, "por unidade", "Tradução de livro publica", "na internet). (20 pontos)"),
    (6, 10, "por unidade", "Tradução de capítulo de l", "na internet). (10 pontos)"),
    (7, 25, "por unidade", "Editor ou organizador de", "nternacional. (25 pontos)"),
    (8, 15, "por unidade", "Editor ou organizador de", "ão nacional). (15 pontos)"),
    (9, 25, "por unidade", "Artigo de pesquisa public", "na internet). (25 pontos)"),
    (10, 20, "por unidade", "Artigo de pesquisa public", "na internet). (20 pontos)"),
    (11, 6, "por unidade", "Artigo de pesquisa public", "na internet). (6 pontos)"),
    (12, 2, "por unidade", "Publicação em sítio eletr", "do (internet). (2 pontos)"),
    (13, 6, "por unidade", "Artigo de revisão, resenh", "na internet). (6 pontos)"),
    (14, 5, "por unidade", "Artigo de revisão, resenh", "na internet). (5 pontos)"),
    (15, 5, "por unidade", "Tradução publicada de art", "na internet). (5 pontos)"),
    (16, 5, "por unidade", "Relatório técnico – deman", "consultoria. ( 5 pontos)"),
    (17, 7, "por unidade", "Produção de manual técnic", "co e didático. (7 pontos)"),
    (18, 2, "por unidade", "Revisão de material didát", "rmas da ABNT. ( 2 pontos)"),
    (19, 10, "por unidade", "Autor de trabalho complet", "ternacional. ( 10 pontos)"),
    (20, 2, "por unidade", "Comunicação de trabalho c", "umo publicado. (2 pontos)"),
    (21, 1, "por unidade", "Comunicação de trabalho s", "umo publicado. ( 1 ponto)"),
    (22, 5, "por unidade", "Apresentação de trabalho", "nternacionais. (5 pontos)"),
    (23, 2, "por unidade", "Apresentação de trabalho", "cos nacionais. (2 pontos)"),
    (24, 10, "por unidade", "Participação como apresen", "sas redondas. (10 pontos)"),
    (25, 1, "por unidade", "Citação ou referência de", "tigo ou livro). (1 ponto)"),
    (26, 4, "por unidade", "Ilustração de livros publ", "ho editorial). (4 pontos)"),
    (27, 4, "por unidade", "Criação de capa de livro", "ho editorial). (4 pontos)"),
    (28, 5, "por unidade", "Produção de livros (desig", "ros (design). ( 5 pontos)"),
    (29, 10, "por unidade", "Patente depositada requer", "da requerida. (10 pontos)"),
    (30, 30, "por unidade", "Patente depositada conced", "a concedida. ( 30 pontos)"),
    (31, 10, "por unidade", "Autor (único) de document", "publicados. ( 10 pontos)"),
    (32, 5, "por unidade", "Coautor de documentos car", "os publicados. (5 pontos)"),
    (33, 15, "por unidade", "Registro de marcas e soft", "softwares. ( 15 pontos )"),
    (34, 20, "por unidade", "Editor Chefe de Revista.", "de Revista. ( 20 pontos )"),
    (35, 10, "por unidade", "Editor Associado de Revis", "de Revista. ( 10 pontos )"),
    (36, 5, "por unidade", "Consultor ad hoc ou revis", "ano/revista). ( 5 pontos)"),
    (37, 0, "sem pontuação", "Afastamento de docente qu", "seu desempenho acadêmico."),
]

EXPECTED = {
    2: GROUP_II,
    3: GROUP_III,
    4: GROUP_IV,
    5: GROUP_V,
    6: GROUP_VI,
    7: GROUP_VII,
    8: GROUP_VIII,
}
MIN_HOURS = {(4, 3): 20, (4, 4): 20, (4, 5): 20}  # "carga horária mínima de 20 h" (IV.3-5)
HOURS_BLOCK = {(7, 11): 30}  # VII.11 "cada 30 horas = 1 ponto"
DUPLICATED_POINTS_TEXT = [(8, 7), (8, 8), (8, 13), (8, 14)]  # the sheet repeats "(N pontos)"
ITEMS = [(g, *row) for g, rows in EXPECTED.items() for row in rows]


@pytest.fixture(scope="module")
def groups():
    data = json.loads((DIR / "ufpa.json").read_text(encoding="utf-8"))
    return {g["number"]: g for g in data["groups"]}


def seeded(groups, group, item):
    (found,) = [c for c in groups[group]["criteria"] if c["item_number"] == item]
    return found


def decimal_or_none(value):
    return None if value is None else Decimal(str(value))


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def test_expected_table_has_97_scored_items_and_the_ministries_leave_item():
    assert len(ITEMS) == 98
    assert [g for g, *_ in ITEMS].count(8) == 37
    assert sum(1 for _, _, points, *_ in ITEMS if points) == 97
    assert sum(points for _, _, points, *_ in ITEMS) == 1311  # GI-12: VI.14 = 3, was 6


def test_seed_has_no_item_outside_the_expected_table(groups):
    seeded_keys = {
        (g, c["item_number"]) for g, grp in groups.items() if g >= 2 for c in grp["criteria"]
    }
    assert seeded_keys == {(g, item) for g, item, *_ in ITEMS}


@pytest.mark.parametrize(
    "group,item,points,unit,start,end", ITEMS, ids=[f"{g}.{i}" for g, i, *_ in ITEMS]
)
def test_item_points_unit_mode_and_minimum_hours(groups, group, item, points, unit, start, end):
    criterion = seeded(groups, group, item)
    block = HOURS_BLOCK.get((group, item))
    assert Decimal(str(criterion["unit_points"])) == points
    assert criterion["unit_label"] == unit
    assert criterion["mode"] == ("POR_BLOCO_DE_HORAS" if block else "POR_UNIDADE")
    assert decimal_or_none(criterion["hours_per_block"]) == block
    minimum = MIN_HOURS.get((group, item))
    assert decimal_or_none(criterion["min_hours"]) == minimum


@pytest.mark.parametrize(
    "group,item,points,unit,start,end", ITEMS, ids=[f"{g}.{i}" for g, i, *_ in ITEMS]
)
def test_item_description_keeps_the_spreadsheet_text(groups, group, item, points, unit, start, end):
    description = normalized(seeded(groups, group, item)["description"])
    assert description.startswith(start)
    assert description.endswith(end)


@pytest.mark.parametrize("key", DUPLICATED_POINTS_TEXT, ids=lambda k: f"{k[0]}.{k[1]}")
def test_the_duplicated_points_text_of_the_sheet_is_collapsed_to_one(groups, key):
    description = normalized(seeded(groups, *key)["description"])
    assert len(re.findall(r"\(\s*\d+\s*pontos?\s*\)", description)) == 1


def test_group_one_rows_are_pit_hours_with_no_points_and_count_in_the_total(groups):
    rows = groups[1]["criteria"]
    assert [
        (c["item_number"], c["mode"], c["unit_label"], c["unit_points"], c["weeks_per_semester"],
         Decimal(str(c["prep_ratio"])), c["min_hours"])
        for c in rows
    ] == [
        (1, "CARGA_SEMANAL", "horas (PIT)", None, 17, 1, None),
        (2, "CARGA_SEMANAL", "horas (PIT)", None, 17, 2, None),
    ]  # fmt: skip
    assert groups[1]["counts_in_total"] is True  # GI-07: was False (PIT-01)
