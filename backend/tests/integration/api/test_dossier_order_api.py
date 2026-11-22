"""ORD-01, ORD-02 (T86): the dossier order route."""

import json
from functools import partial

from app.infrastructure.documents.config_loader import load_dossier_order


def test_the_list_follows_the_file_with_the_five_generated_documents_marked(client, admin):
    response = client.get("/api/dossier-order")

    assert response.status_code == 200
    items = response.json()
    assert [i["order"] for i in items] == sorted(i["order"] for i in items)
    assert [i["title"] for i in items[:3]] == [
        "Requerimento à CPPD, conforme o modelo",
        "Portaria da última progressão",
        "Declaração de pagamento de exercícios anteriores, preenchida",
    ]
    marked = [(i["order"], i["generated_by"]) for i in items if i["generated_by"]]
    assert len(items) == 9
    assert [kind for _, kind in marked] == [
        "REQUERIMENTO",
        "RELATORIO",
        "TABELA",
        "COMPROVANTE",
        "PARECER",
    ]
    assert [i["title"] for i in items[-2:]] == ["Portaria da banca", "Parecer da banca"]
    assert set(items[0]) == {"order", "title", "generated_by"}
    assert items[0]["generated_by"] == "REQUERIMENTO"
    assert items[1]["generated_by"] is None


def test_the_route_reads_the_configuration_file_at_every_call(client, admin, tmp_path):
    path = tmp_path / "dossier_order.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "order": 1,
                        "key": "TABELA",
                        "title": "Primeiro",
                        "source": "GERADO",
                        "generated_by": "TABELA",
                    }
                ]
            }
        )
    )
    client.app.state.container.dossier_order = partial(load_dossier_order, path)
    assert client.get("/api/dossier-order").json() == [
        {"order": 1, "title": "Primeiro", "generated_by": "TABELA"}
    ]

    path.write_text(
        json.dumps(
            {
                "items": [
                    {"order": 1, "key": "LATTES", "title": "Segundo", "source": "MANUAL"},
                    {
                        "order": 2,
                        "key": "RELATORIO",
                        "title": "Primeiro",
                        "source": "GERADO",
                        "generated_by": "RELATORIO",
                    },
                ]
            }
        )
    )

    assert [i["title"] for i in client.get("/api/dossier-order").json()] == ["Segundo", "Primeiro"]


def test_a_session_is_required(client):
    assert client.get("/api/dossier-order").status_code == 401
