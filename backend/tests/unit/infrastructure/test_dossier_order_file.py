"""ORD-01, ORD-02, DOS-01: the order of the dossier that ships with the system."""

from app.domain.entities.generated import DocumentKind
from app.domain.entities.report import DossierSource
from app.infrastructure.documents.config_loader import load_dossier_order


def test_the_order_of_the_file_is_the_order_of_the_dossier():
    items = load_dossier_order()

    assert [i.order for i in items] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    titles = [i.title for i in items]
    assert titles[0].startswith("Requerimento à CPPD")
    assert titles[1].startswith("Portaria da última progressão")
    assert titles[2].startswith("Declaração de pagamento de exercícios anteriores")
    assert titles[3].startswith("Relatório")
    assert titles[4] == "Tabela de Pontuação"
    assert titles[5].startswith("Documentação comprobatória")
    assert titles[6].startswith("Currículo Lattes")
    assert titles[7] == "Portaria da banca"
    assert titles[8] == "Parecer da banca"


def test_each_item_has_its_key_in_the_order_of_the_dossier():
    assert [i.key for i in load_dossier_order()] == [
        "REQUERIMENTO",
        "PORTARIA_ULTIMA_PROGRESSAO",
        "DECLARACAO_EXERCICIOS_ANTERIORES",
        "RELATORIO",
        "TABELA",
        "COMPROVANTE",
        "CURRICULO_LATTES",
        "PORTARIA_BANCA",
        "PARECER",
    ]


def test_the_five_documents_the_system_writes_are_generated_in_the_order_of_the_file():
    items = load_dossier_order()

    generated = [(i.key, i.generated_by) for i in items if i.generated_by]
    assert generated == [
        ("REQUERIMENTO", DocumentKind.REQUERIMENTO),
        ("RELATORIO", DocumentKind.RELATORIO),
        ("TABELA", DocumentKind.TABELA),
        ("COMPROVANTE", DocumentKind.COMPROVANTE),
        ("PARECER", DocumentKind.PARECER),
    ]


def test_the_source_of_each_item_says_who_produces_it():
    sources = {i.key: i.source for i in load_dossier_order()}

    assert sources["PORTARIA_BANCA"] is DossierSource.PORTARIA_BANCA
    assert {k for k, s in sources.items() if s is DossierSource.MANUAL} == {
        "PORTARIA_ULTIMA_PROGRESSAO",
        "DECLARACAO_EXERCICIOS_ANTERIORES",
        "CURRICULO_LATTES",
    }
    assert {k for k, s in sources.items() if s is DossierSource.GERADO} == {
        "REQUERIMENTO",
        "RELATORIO",
        "TABELA",
        "COMPROVANTE",
        "PARECER",
    }


def test_the_table_goes_after_the_report_and_before_the_proof():
    kinds = [i.generated_by for i in load_dossier_order() if i.generated_by]
    assert kinds.index(DocumentKind.RELATORIO) < kinds.index(DocumentKind.TABELA)
    assert kinds.index(DocumentKind.TABELA) < kinds.index(DocumentKind.COMPROVANTE)


def test_the_two_board_documents_close_the_dossier():
    assert [i.key for i in load_dossier_order()[-2:]] == ["PORTARIA_BANCA", "PARECER"]
