"""User management routes, ADMIN only (AUTH-10, AUD-01)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.users import NewUser
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.users import UserAdminOut, UserCreate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(
    body: UserCreate,
    actor: Annotated[User, Depends(current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> UserAdminOut:
    data = NewUser(
        email=body.email,
        name=body.name,
        role=body.role,
        password=body.password,
        professor_id=body.professor_id,
        unit_ids=frozenset(body.unit_ids),
    )
    user = await run_in_threadpool(container.create_user.execute, actor, data)
    return UserAdminOut.of(user)


@router.get("", response_model=list[UserAdminOut])
async def list_users(
    actor: Annotated[User, Depends(current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> list[UserAdminOut]:
    users = await run_in_threadpool(container.list_users.execute, actor)
    return [UserAdminOut.of(u) for u in users]
