"""SEC-01, SEC-07, DUP-07: ActivityOut carries the validity, the merged activities and the
predicted points; the input models still refuse unknown fields."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.entities.activity import Activity
from app.domain.rules.activity_validity import InvalidReason, Validity, ValidityState
from app.presentation.schemas.activities import (
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    MergedOut,
)

D = Decimal


def activity(**kw) -> Activity:
    return Activity(
        id=uuid.uuid4(), process_id=uuid.uuid4(), created_by=uuid.uuid4(), title="Banca", **kw
    )


def test_a_valid_activity_with_a_prediction_serializes_validity_merged_and_points():
    merged_id = uuid.uuid4()

    body = ActivityOut.of(
        activity(group_number=3, item_number=4),
        validity=Validity(ValidityState.VALIDA),
        merged=[MergedOut(id=merged_id, title="Banca repetida")],
        predicted_points=D("5"),
    ).model_dump(mode="json")

    assert body["validity"] == {
        "state": "VALIDA",
        "reason": None,
        "needs_category": False,
        "params": {},
    }
    assert body["merged"] == [{"id": str(merged_id), "title": "Banca repetida"}]
    assert body["predicted_points"] == "5.00"


def test_a_not_valid_activity_by_date_carries_the_dates_as_iso_text():
    validity = Validity(
        ValidityState.NAO_VALIDA,
        InvalidReason.FORA_DO_INTERSTICIO,
        False,
        {
            "event_date": date(2020, 1, 10),
            "interstice_start": date(2022, 11, 23),
            "interstice_end": date(2024, 11, 23),
        },
    )

    body = ActivityOut.of(activity(), validity=validity).model_dump(mode="json")

    assert body["validity"]["state"] == "NAO_VALIDA"
    assert body["validity"]["reason"] == "FORA_DO_INTERSTICIO"
    assert body["validity"]["params"] == {
        "event_date": "2020-01-10",
        "interstice_start": "2022-11-23",
        "interstice_end": "2024-11-23",
    }


def test_a_not_valid_activity_by_hours_carries_the_hours_as_text():
    validity = Validity(
        ValidityState.NAO_VALIDA,
        InvalidReason.CARGA_HORARIA_INSUFICIENTE,
        False,
        {"hours": D("19.00"), "min_hours": D("20")},
    )

    body = ActivityOut.of(activity(), validity=validity).model_dump(mode="json")

    assert body["validity"]["params"] == {"hours": "19", "min_hours": "20"}


def test_an_activity_that_needs_a_category_says_so_and_has_no_prediction():
    body = ActivityOut.of(
        activity(), validity=Validity(ValidityState.VALIDA, needs_category=True)
    ).model_dump(mode="json")

    assert body["validity"]["needs_category"] is True
    assert body["predicted_points"] is None  # no prediction without one


def test_without_validity_merged_or_points_the_fields_are_empty():
    body = ActivityOut.of(activity()).model_dump(mode="json")

    assert body["validity"] is None
    assert body["merged"] == []
    assert body["predicted_points"] is None


def test_the_new_fields_add_no_personal_data():
    body = ActivityOut.of(
        activity(),
        validity=Validity(ValidityState.VALIDA),
        merged=[MergedOut(id=uuid.uuid4(), title="Banca repetida")],
        predicted_points=D("1"),
    ).model_dump(mode="json")

    assert set(body["merged"][0]) == {"id", "title"}
    assert set(body["validity"]) == {"state", "reason", "needs_category", "params"}


@pytest.mark.parametrize("extra", ["validity", "merged", "predicted_points"])
def test_the_input_models_still_refuse_the_output_only_fields(extra):
    ActivityCreate(title="Banca")  # accepted without the extra field
    ActivityUpdate(title="Banca", expected_version=1)

    with pytest.raises(ValidationError):
        ActivityCreate(title="Banca", **{extra: None})
    with pytest.raises(ValidationError):
        ActivityUpdate(title="Banca", expected_version=1, **{extra: None})
