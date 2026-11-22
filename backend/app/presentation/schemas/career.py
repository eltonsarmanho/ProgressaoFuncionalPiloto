"""Career version schemas (CARR-08); `definition` follows design.md Data Models."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.career import VersionView
from app.domain.entities.career import CareerClass, CareerVersion
from app.domain.entities.professor import Titration


class CareerClassIn(BaseModel):
    code: str
    denominations: list[str]
    levels: list[int]
    promotion_min_months: int | None = None
    required_titration: Titration | None = None  # NTIT-05: None, no titration rule


def _blank_to_none(value: str | None) -> str | None:
    return (value or "").strip() or None


class CareerVersionIn(BaseModel):
    name: str
    valid_from: date | None = None
    valid_to: date | None = None
    norm_reference: str
    progression_min_months: int
    classes: list[CareerClassIn]
    norm_code: str | None = None
    required_titration_norm_code: str | None = None

    def unset_links(self) -> frozenset[str]:
        """The link fields the request left out, so that an old body does not erase them: a
        field sent as null is cleared, a field not sent keeps the stored value."""
        names = {
            name
            for name in ("norm_code", "required_titration_norm_code")
            if name not in self.model_fields_set
        }
        names |= {
            f"required_titration:{c.code}"
            for c in self.classes
            if "required_titration" not in c.model_fields_set
        }
        return frozenset(names)

    def to_entity(self) -> CareerVersion:
        return CareerVersion(
            name=self.name,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            norm_reference=self.norm_reference,
            progression_min_months=self.progression_min_months,
            classes=tuple(
                CareerClass(
                    code=c.code,
                    denominations=tuple(c.denominations),
                    levels=tuple(c.levels),
                    promotion_min_months=c.promotion_min_months,
                    required_titration=c.required_titration,
                )
                for c in self.classes
            ),
            norm_code=_blank_to_none(self.norm_code),
            required_titration_norm_code=_blank_to_none(self.required_titration_norm_code),
        )


class CareerVersionOut(CareerVersionIn):
    id: UUID
    in_use: bool

    @classmethod
    def of(cls, view: VersionView) -> "CareerVersionOut":
        v = view.version
        return cls(
            id=v.id,
            in_use=view.in_use,
            name=v.name,
            valid_from=v.valid_from,
            valid_to=v.valid_to,
            norm_reference=v.norm_reference,
            progression_min_months=v.progression_min_months,
            classes=[
                CareerClassIn(
                    code=c.code,
                    denominations=list(c.denominations),
                    levels=list(c.levels),
                    promotion_min_months=c.promotion_min_months,
                    required_titration=c.required_titration,
                )
                for c in v.classes
            ],
            norm_code=v.norm_code,
            required_titration_norm_code=v.required_titration_norm_code,
        )
