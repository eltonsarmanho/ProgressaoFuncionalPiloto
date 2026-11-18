"""REL-03, REL-06: only the fields of the activity go to the AI, with the identifiers masked."""

import json
from datetime import date
from decimal import Decimal

from app.domain.entities.activity import Level
from app.domain.rules.report_wording import build_wording_items
from tests.unit.domain.comprovante_support import make_activity
from tests.unit.domain.scenario_211 import official_like_table

ALL_KEYS = {
    "id",
    "tipo",
    "titulo",
    "datas",
    "carga_horaria",
    "carga_horaria_curso",
    "periodo_letivo",
    "quantidade",
    "descricao",
}


def full_activity(**kwargs):
    defaults = {
        "title": "Oficina de dados abertos",
        "description": "Oficina para docentes da unidade.",
        "event_date": date(2023, 6, 1),
        "hours": Decimal("8"),
        "course_hours": Decimal("60"),
        "academic_period": "2023.1",
        "quantity": Decimal("2"),
        "level": Level.GRADUACAO,
        "evidence_note": "Declaração assinada pelo Prof. Fulano, SIAPE 1234567",
    }
    defaults.update(kwargs)
    return make_activity(4, 4, **defaults)


def payload_of(activity, version=None):
    return build_wording_items([activity], version)[0].payload()


def test_the_payload_has_the_fields_of_the_activity_and_nothing_else():
    version = official_like_table()

    payload = payload_of(full_activity(), version)

    assert set(payload) == ALL_KEYS


def test_the_payload_values_are_the_formatted_fields_and_the_criterion_type():
    activity = full_activity()

    payload = payload_of(activity, official_like_table())

    assert payload == {
        "id": str(activity.id),
        "tipo": "Critério 4.4",
        "titulo": "Oficina de dados abertos",
        "datas": "01/06/2023",
        "carga_horaria": "8 h",
        "carga_horaria_curso": "60 h",
        "periodo_letivo": "1º Período de 2023",
        "quantidade": "2",
        "descricao": "Oficina para docentes da unidade.",
    }


def test_the_payload_never_carries_the_evidence_note_the_author_or_the_process():
    activity = full_activity()

    sent = json.dumps(payload_of(activity, official_like_table()), ensure_ascii=False)

    assert "Declaração assinada" not in sent
    assert "SIAPE" not in sent and "1234567" not in sent
    assert str(activity.created_by) not in sent
    assert str(activity.process_id) not in sent


def test_the_description_is_sent_after_masking_cpf_email_and_phone():
    activity = full_activity(
        description=(
            "Contato: fulana@exemplo.org, CPF 123.456.789-09, telefone (91) 98888-7777. "
            "Oficina para docentes."
        )
    )

    description = payload_of(activity)["descricao"]

    assert "fulana@exemplo.org" not in description
    assert "123.456.789-09" not in description
    assert "98888-7777" not in description
    assert description == (
        "Contato: [EMAIL], CPF [CPF], telefone [TELEFONE]. Oficina para docentes."
    )


def test_the_title_is_masked_too():
    activity = full_activity(title="Atendimento de fulana@exemplo.org")

    assert payload_of(activity)["titulo"] == "Atendimento de [EMAIL]"


def test_a_field_without_value_is_left_out():
    activity = make_activity(4, 4, title="Banca de TCC", event_date=None)

    payload = payload_of(activity)

    assert set(payload) == {"id", "titulo"}


def test_the_type_is_left_out_without_a_table_or_without_the_criterion():
    activity = full_activity()
    other = make_activity(8, 1, title="Sem critério na tabela")

    assert "tipo" not in payload_of(activity)
    assert "tipo" not in payload_of(other, official_like_table())


def test_the_dates_of_a_period_come_in_portuguese():
    activity = make_activity(
        4, 4, event_date=None, period_start=date(2023, 3, 1), period_end=date(2023, 7, 15)
    )

    assert payload_of(activity)["datas"] == "01/03/2023 a 15/07/2023"


def test_there_is_one_item_per_activity_in_the_order_given():
    first, second = full_activity(title="Primeira"), full_activity(title="Segunda")

    items = build_wording_items([second, first])

    assert [i.activity_id for i in items] == [second.id, first.id]


def test_the_facts_to_check_the_wording_are_the_payload_without_the_id():
    activity = full_activity()

    item = build_wording_items([activity], official_like_table())[0]

    assert item.fields == {k: v for k, v in item.payload().items() if k != "id"}
    assert "id" not in item.fields
