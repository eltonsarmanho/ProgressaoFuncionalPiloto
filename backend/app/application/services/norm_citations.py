"""Resolves the norm codes carried by alerts into citations (NLINK-03, NLINK-05)."""

import logging
from collections.abc import Iterable, Mapping

from app.domain.entities.norm import NormCitation
from app.domain.repositories.ports import UnitOfWork

logger = logging.getLogger(__name__)


def cite_norms(uow: UnitOfWork, codes: Iterable[str | None]) -> Mapping[str, NormCitation]:
    """One query for every code; a code with no registered norm is left out and logged, so its
    alert shows only the `norm_reference` text."""
    wanted = {c for c in codes if c}
    if not wanted:
        return {}
    found = uow.norms.by_codes(wanted)
    for code in sorted(wanted - found.keys()):
        logger.warning("norma não cadastrada: %s", code)
    return {code: norm.citation() for code, norm in found.items()}
