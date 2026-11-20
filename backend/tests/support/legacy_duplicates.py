"""A duplicate activity inserted straight into the database.

Since DUP-04 every write merges the duplicates of the process, so a test that needs two duplicates
side by side (the "distinct" mark, the duplicate reason of the engine) builds the second one as
the data of a process from before the merge existed: a row the repository holds, never merged.
"""

import uuid
from dataclasses import replace

from app.domain.entities.activity import Activity


def add_legacy_duplicate(uow_factory, original: Activity, **changes) -> Activity:
    """A copy of `original` (same item, date and, by default, status) created after it."""
    twin = replace(
        original,
        id=uuid.uuid4(),
        created_at=None,
        updated_at=None,
        version=1,
        distinct_justification=None,
        merged_into_id=None,
        **changes,
    )
    with uow_factory() as uow:
        uow.activities.add(twin)
        uow.commit()
        return uow.activities.get(twin.id)
