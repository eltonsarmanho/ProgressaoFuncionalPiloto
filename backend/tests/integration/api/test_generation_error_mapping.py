"""TAB-07, DEL-12, DEL-14, VER-04: HTTP mapping of the generation and gone errors."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities.generated import GenerationCode
from app.domain.errors import (
    Conflict,
    GenerationRefused,
    Gone,
    NotFound,
    StaleVersion,
    ValidationFailed,
)
from app.presentation.errors import install_error_handlers

RAISED = {
    "refused": GenerationRefused("SEM_ATIVIDADES_VALIDADAS", "Nenhuma atividade validada"),
    "no_category": GenerationRefused(
        GenerationCode.ATIVIDADE_SEM_CATEGORIA, "Há atividades sem categoria na Etapa 3."
    ),
    "gone": Gone("ARQUIVO_EXCLUIDO", "O arquivo foi excluído"),
    "conflict_code": Conflict("Já existe uma geração em andamento", code="GERACAO_EM_ANDAMENTO"),
    "conflict": Conflict("Processo concluído ou arquivado não pode ser alterado"),
    "stale": StaleVersion("A atividade foi alterada por outro usuário; recarregue"),
    "not_found": NotFound("Processo não encontrado"),
    "invalid": ValidationFailed("unit_id", "Unidade inexistente"),
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/raise/{name}")
    def raise_error(name: str):
        raise RAISED[name]

    @app.get("/typed/{count}")
    def typed(count: int):
        return {"count": count}

    return TestClient(app)


def test_a_generation_refusal_is_422_with_field_code_and_message(client):
    response = client.get("/raise/refused")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "field": "geracao",
                "code": "SEM_ATIVIDADES_VALIDADAS",
                "message": "Nenhuma atividade validada",
            }
        ]
    }


def test_the_refusal_of_an_activity_without_category_is_422_with_its_code(client):
    # SEG-05
    response = client.get("/raise/no_category")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "field": "geracao",
                "code": "ATIVIDADE_SEM_CATEGORIA",
                "message": "Há atividades sem categoria na Etapa 3.",
            }
        ]
    }


def test_a_gone_error_is_410_with_field_code_and_message(client):
    response = client.get("/raise/gone")

    assert response.status_code == 410
    assert response.json() == {
        "detail": [
            {"field": "arquivo", "code": "ARQUIVO_EXCLUIDO", "message": "O arquivo foi excluído"}
        ]
    }


def test_a_conflict_with_a_code_is_409_and_returns_the_code_in_the_body(client):
    response = client.get("/raise/conflict_code")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Já existe uma geração em andamento",
        "code": "GERACAO_EM_ANDAMENTO",
    }


def test_a_conflict_without_a_code_keeps_the_old_409_body(client):
    response = client.get("/raise/conflict")

    assert response.status_code == 409
    assert response.json() == {"detail": "Processo concluído ou arquivado não pode ser alterado"}


def test_a_stale_version_keeps_the_old_409_body(client):
    response = client.get("/raise/stale")

    assert response.status_code == 409
    assert response.json() == {"detail": "A atividade foi alterada por outro usuário; recarregue"}


def test_not_found_and_field_validation_answer_as_before(client):
    not_found = client.get("/raise/not_found")
    invalid = client.get("/raise/invalid")
    malformed = client.get("/typed/abc")

    assert (not_found.status_code, not_found.json()) == (404, {"detail": "Processo não encontrado"})
    assert (invalid.status_code, invalid.json()) == (
        422,
        {"detail": [{"field": "unit_id", "message": "Unidade inexistente"}]},
    )
    assert malformed.status_code == 422
    assert [e["field"] for e in malformed.json()["detail"]] == ["count"]
