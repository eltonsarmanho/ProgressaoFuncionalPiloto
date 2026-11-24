"""TAB-01, TAB-04: compute_process_score runs without an actor and equals the screen result."""

from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData, compute_process_score
from app.domain.errors import NotFound
from app.domain.rules.scoring_verification import MinimumStatus

D = Decimal


def add(world, title, group, item, **kw):
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title=title, group_number=group, item_number=item, event_date=date(2023, 5, 10), **kw
        ),
    )


def test_it_returns_what_the_use_case_returns_without_receiving_an_actor(world, official_chosen):
    add(world, "Orientação", 2, 7, quantity=D("4"))
    add(world, "Banca", 3, 2)
    via_use_case = world.calc.execute(world.admin, world.process.id)

    with world.uow_factory() as uow:
        direct = compute_process_score(uow, uow.processes.get(world.process.id))

    assert direct == via_use_case
    assert direct.chosen.version.id == world.official_version.id
    assert direct.result.counters.activities == 2


def test_without_a_chosen_table_it_gives_the_no_table_result(world):
    add(world, "Banca", 3, 2)

    with world.uow_factory() as uow:
        direct = compute_process_score(uow, uow.processes.get(world.process.id))

    assert direct.chosen is None
    assert direct.result.total == 0
    assert direct.minimum.status is MinimumStatus.NAO_DEFINIDO


def test_the_use_case_still_checks_access_before_computing(world, official_chosen):
    with pytest.raises(NotFound):
        world.calc.execute(world.other_docente, world.process.id)
