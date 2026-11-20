"""REL-12, REL-02: the deterministic text of an entry from the template and the activity fields."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import PeriodPrecision
from app.domain.entities.report import EntrySpec
from app.domain.rules.report_draft import propose_draft, template_text
from tests.unit.domain.comprovante_support import make_activity
from tests.unit.domain.report_support import group_map, template


def teaching(**kwargs):
    defaults = {
        "title": "Algoritmos e Estruturas de Dados",
        "course_hours": Decimal("60.00"),
        "academic_period": "2023.1",
    }
    defaults.update(kwargs)
    return make_activity(1, 1, **defaults)


def test_a_line_is_filled_with_the_title_and_the_formatted_date_and_hours():
    activity = make_activity(
        4, 4, title="Oficina de dados", event_date=date(2023, 6, 1), hours=Decimal("7.5")
    )
    spec = EntrySpec(line="{title}, {dates}, {hours}")

    assert template_text(spec, activity) == "Oficina de dados, 01/06/2023, 7,5 h"


def test_the_hours_the_period_and_the_dates_come_out_in_portuguese():
    activity = teaching(event_date=date(2023, 3, 20))
    spec = EntrySpec(
        fields=(
            ("Disciplina", "{title}"),
            ("Carga horária", "{course_hours}"),
            ("Período", "{period}"),
            ("Data", "{dates}"),
        )
    )

    assert template_text(spec, activity) == (
        "Disciplina: Algoritmos e Estruturas de Dados\n"
        "Carga horária: 60 h\n"
        "Período: 1º Período de 2023\n"
        "Data: 20/03/2023"
    )


def test_an_academic_period_out_of_the_usual_format_is_written_as_typed():
    activity = teaching(academic_period="Verão 2023")

    assert template_text(EntrySpec(line="{period}"), activity) == "Verão 2023"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"event_date": date(2024, 11, 23)}, "23/11/2024"),
        (
            {"event_date": None, "period_start": date(2023, 3, 1), "period_end": date(2023, 7, 15)},
            "01/03/2023 a 15/07/2023",
        ),
        ({"event_date": None, "period_start": date(2023, 3, 1)}, "desde 01/03/2023"),
        ({"event_date": None, "period_end": date(2023, 7, 15)}, "até 15/07/2023"),
        (
            {
                "event_date": None,
                "period_start": date(2023, 3, 1),
                "period_end": date(2023, 7, 31),
                "period_precision": PeriodPrecision.MONTH,
            },
            "03/2023 a 07/2023",
        ),
    ],
)
def test_the_dates_marker_writes_the_event_the_period_or_the_open_start(kwargs, expected):
    activity = make_activity(4, 4, **kwargs)

    assert template_text(EntrySpec(line="{dates}"), activity) == expected


def test_an_activity_without_funding_source_collaborators_or_ordinance_gets_no_such_lines():
    activity = make_activity(5, 1, title="Projeto de pesquisa sintético")
    spec = EntrySpec(
        fields=(
            ("Projeto", "{title}"),
            ("Fonte do recurso", "{funding_source}"),
            ("Colaboradores", "{collaborators}"),
            ("Portaria nº", "{ordinance_number}"),
        )
    )

    text = template_text(spec, activity)

    assert text == "Projeto: Projeto de pesquisa sintético"
    assert "Fonte" not in text and "Colaboradores" not in text and "Portaria" not in text


def test_a_field_whose_value_is_missing_is_omitted_and_the_others_stay():
    activity = teaching(course_hours=None)
    spec = EntrySpec(fields=(("Disciplina", "{title}"), ("Carga horária", "{course_hours}")))

    assert template_text(spec, activity) == "Disciplina: Algoritmos e Estruturas de Dados"


def test_a_bracketed_part_of_a_line_is_dropped_when_it_has_no_value():
    activity = make_activity(4, 4, title="Oficina de dados", event_date=None)
    spec = EntrySpec(line="{title}[, {dates}][, {hours}]")

    assert template_text(spec, activity) == "Oficina de dados"


def test_a_description_marker_writes_the_description_of_the_activity():
    activity = make_activity(4, 4, description="Oficina para docentes da unidade.")
    spec = EntrySpec(fields=(("Descrição", "{description}"),))

    assert template_text(spec, activity) == "Descrição: Oficina para docentes da unidade."


def test_the_course_appears_when_the_title_names_it():
    activity = teaching(title="Cálculo I - Licenciatura em Matemática")
    spec = EntrySpec(fields=(("Disciplina", "{title}"), ("Curso", "{course}")))

    assert template_text(spec, activity).splitlines()[-1] == "Curso: Licenciatura em Matemática"


def test_the_course_appears_when_the_description_names_it():
    activity = teaching(description="Disciplina ofertada ao curso de Engenharia Civil, turma A.")
    spec = EntrySpec(fields=(("Curso", "{course}"),))

    assert template_text(spec, activity) == "Curso: Engenharia Civil"


def test_the_course_does_not_appear_when_neither_title_nor_description_names_it():
    activity = teaching(description="Disciplina ofertada no segundo ano.")
    spec = EntrySpec(fields=(("Disciplina", "{title}"), ("Curso", "{course}")))

    assert template_text(spec, activity) == "Disciplina: Algoritmos e Estruturas de Dados"


def test_a_value_that_looks_like_a_marker_is_written_as_it_is():
    activity = make_activity(4, 4, title="Curso {hours} [extra]", hours=Decimal("10"))

    assert template_text(EntrySpec(line="{title}"), activity) == "Curso {hours} [extra]"


def test_the_proposed_entries_carry_the_text_of_the_template():
    activity = teaching(event_date=None)

    draft = propose_draft(template(), [activity], group_map(), process_id=activity.process_id)

    entry = next(e for s in draft.sections if s.key == "1.1" for e in s.entries)
    assert entry.text == (
        "Disciplina: Algoritmos e Estruturas de Dados\n"
        "Carga horária: 60 h\n"
        "Período: 1º Período de 2023"
    )
