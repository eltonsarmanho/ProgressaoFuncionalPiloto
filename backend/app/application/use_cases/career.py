"""Career version administration (CARR-08) with audit trail (AUD-01).

Versions are immutable once a process falls inside their validity. Overlapping
validities are rejected: they would change which version existing processes use.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.users import require_admin
from app.domain.entities.audit import AuditAction
from app.domain.entities.career import CareerVersion
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.repositories.ports import UnitOfWork

ENTITY = "career_version"


@dataclass(frozen=True)
class VersionView:
    version: CareerVersion
    in_use: bool


def _audit_view(v: CareerVersion) -> dict:
    return {
        "name": v.name,
        "valid_from": v.valid_from,
        "valid_to": v.valid_to,
        "norm_reference": v.norm_reference,
        "progression_min_months": v.progression_min_months,
        "classes": [
            {
                "code": c.code,
                "denominations": list(c.denominations),
                "levels": list(c.levels),
                "promotion_min_months": c.promotion_min_months,
            }
            for c in v.classes
        ],
    }


def _validate(v: CareerVersion) -> CareerVersion:
    name, reference = v.name.strip(), v.norm_reference.strip()
    if not name:
        raise ValidationFailed("name", "Nome da versão é obrigatório")
    if not reference:
        raise ValidationFailed("norm_reference", "Referência normativa é obrigatória")
    if v.valid_from and v.valid_to and v.valid_to < v.valid_from:
        raise ValidationFailed("valid_to", "Fim da vigência anterior ao início")
    if v.progression_min_months <= 0:
        raise ValidationFailed("progression_min_months", "Interstício deve ser positivo")
    if not v.classes:
        raise ValidationFailed("classes", "A versão deve ter ao menos uma classe")
    codes = [c.code.strip() for c in v.classes]
    if any(not code for code in codes) or len(set(codes)) != len(codes):
        raise ValidationFailed("classes", "Códigos de classe devem ser únicos e não vazios")
    for c in v.classes:
        if not c.denominations or any(not d.strip() for d in c.denominations):
            raise ValidationFailed("classes", f"Classe {c.code}: denominações inválidas")
        if not c.levels or c.levels[0] < 1 or list(c.levels) != sorted(set(c.levels)):
            raise ValidationFailed("classes", f"Classe {c.code}: níveis inválidos")
        if c.promotion_min_months is not None and c.promotion_min_months <= 0:
            raise ValidationFailed("classes", f"Classe {c.code}: interstício de promoção inválido")
    return replace(v, name=name, norm_reference=reference)


def _overlaps(a: CareerVersion, b: CareerVersion) -> bool:
    a_starts_before_b_ends = (
        a.valid_from is None or b.valid_to is None or a.valid_from <= b.valid_to
    )
    b_starts_before_a_ends = (
        b.valid_from is None or a.valid_to is None or b.valid_from <= a.valid_to
    )
    return a_starts_before_b_ends and b_starts_before_a_ends


def _in_use(uow: UnitOfWork, structure_id: UUID, version: CareerVersion) -> bool:
    """A process of this structure whose interstice end date the version covers (CARR-01)."""
    for process in uow.processes.list():
        professor = uow.professors.get(process.professor_id)
        if professor.career_structure_id == structure_id and version.covers(process.end_date):
            return True
    return False


def _structure(uow: UnitOfWork, code: str) -> UUID:
    structure_id = uow.career_versions.structure_id(code)
    if structure_id is None:
        raise NotFound("Estrutura de carreira não encontrada")
    return structure_id


def _reject_overlap(existing: Sequence[CareerVersion], version: CareerVersion) -> None:
    for other in existing:
        if other.id != version.id and _overlaps(other, version):
            raise Conflict(f'Vigência sobrepõe a versão "{other.name}"')


class ListCareerVersions:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, code: str) -> Sequence[VersionView]:
        with self._uow_factory() as uow:
            structure_id = _structure(uow, code)
            return [
                VersionView(v, _in_use(uow, structure_id, v))
                for v in uow.career_versions.list_versions(code)
            ]


class CreateCareerVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, code: str, version: CareerVersion) -> VersionView:
        require_admin(actor)
        version = replace(_validate(version), id=uuid.uuid4())
        with self._uow_factory() as uow:
            _structure(uow, code)
            _reject_overlap(uow.career_versions.list_versions(code), version)
            uow.career_versions.add(code, version)
            self._audit.record(
                uow, actor.id, ENTITY, version.id, AuditAction.CREATE, {}, _audit_view(version)
            )
            uow.commit()
        return VersionView(version, False)


class UpdateCareerVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self, actor: User, code: str, version_id: UUID, version: CareerVersion
    ) -> VersionView:
        require_admin(actor)
        version = replace(_validate(version), id=version_id)
        with self._uow_factory() as uow:
            structure_id = _structure(uow, code)
            existing = uow.career_versions.list_versions(code)
            current = next((v for v in existing if v.id == version_id), None)
            if current is None:
                raise NotFound("Versão de carreira não encontrada")
            if _in_use(uow, structure_id, current):
                raise Conflict("Versão já usada por processos não pode ser alterada")
            _reject_overlap(existing, version)
            uow.career_versions.update(version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                version.id,
                AuditAction.UPDATE,
                _audit_view(current),
                _audit_view(version),
            )
            in_use = _in_use(uow, structure_id, version)
            uow.commit()
        return VersionView(version, in_use)
