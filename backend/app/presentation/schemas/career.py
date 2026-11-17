"""Career version schemas (CARR-08); `definition` follows design.md Data Models."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.career import VersionView
from app.domain.entities.career import CareerClass, CareerVersion


class CareerClassIn(BaseModel):
    code: str
    denominations: list[str]
    levels: list[int]
    promotion_min_months: int | None = None


class CareerVersionIn(BaseModel):
    name: str
    valid_from: date | None = None
    valid_to: date | None = None
    norm_reference: str
    progression_min_months: int
    classes: list[CareerClassIn]

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
                )
                for c in self.classes
            ),
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
                )
                for c in v.classes
            ],
        )
