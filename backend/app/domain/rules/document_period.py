"""Whether a whole document lies outside the process interstice (FORA-01, FORA-05, FORA-06)."""

from collections.abc import Iterable

from app.domain.rules.scoring_periods import PeriodState

_NO_USABLE_DATE = (None, PeriodState.SEM_DATA, PeriodState.NAO_VERIFICAVEL)


def document_outside_interstice(period_states: Iterable[PeriodState | None]) -> bool:
    """True when at least one activity has a usable date and every dated activity is `FORA`.

    An activity inside the interstice (`DENTRO`) or crossing its limit (`PARCIAL`) keeps the
    document in. Activities without a usable date are ignored; with none dated at all the rule
    does not apply.
    """
    dated = [state for state in period_states if state not in _NO_USABLE_DATE]
    return bool(dated) and all(state is PeriodState.FORA for state in dated)
