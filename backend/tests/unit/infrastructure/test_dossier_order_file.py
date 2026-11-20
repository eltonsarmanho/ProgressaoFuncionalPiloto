"""ORD-01, ORD-02: the order of the dossier that ships with the system."""

from app.domain.entities.generated import DocumentKind
from app.infrastructure.documents.config_loader import load_dossier_order


def test_the_order_of_the_file_is_the_order_of_the_dossier():
    items = load_dossier_order()

    assert [i.order for i in items] == [1, 2, 3, 4, 5, 6, 7]
    titles = [i.title for i in items]
    assert titles[0].startswith("Requerimento à CPPD")
    assert titles[1].startswith("Portaria da última progressão")
    assert titles[2].startswith("Declaração de pagamento de exercícios anteriores")
    assert titles[3].startswith("Relatório")
    assert titles[4] == "Tabela de Pontuação"
    assert titles[5].startswith("Documentação comprobatória")
    assert titles[6].startswith("Currículo Lattes")


def test_only_the_report_the_table_and_the_proof_are_generated_by_the_system():
    items = load_dossier_order()

    generated = {i.title.split(",")[0]: i.generated_by for i in items if i.generated_by}
    assert generated == {
        "Relatório de progressão funcional": DocumentKind.RELATORIO,
        "Tabela de Pontuação": DocumentKind.TABELA,
        "Documentação comprobatória": DocumentKind.COMPROVANTE,
    }
    assert sum(1 for i in items if i.generated_by is None) == 4


def test_the_table_goes_after_the_report_and_before_the_proof():
    kinds = [i.generated_by for i in load_dossier_order() if i.generated_by]
    assert kinds == [DocumentKind.RELATORIO, DocumentKind.TABELA, DocumentKind.COMPROVANTE]
