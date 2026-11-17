"""Auth routes (AUTH-01, AUTH-02, AUTH-11)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import Session, User
from app.presentation.csrf import SESSION_COOKIE
from app.presentation.dependencies import Container, current_session, current_user, get_container
from app.presentation.schemas.auth import LoginRequest, MeOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginRequest,
    response: Response,
    container: Annotated[Container, Depends(get_container)],
) -> UserOut:
    result = await run_in_threadpool(container.login.execute, body.email, body.password)
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        httponly=True,
        secure=container.settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return UserOut(id=result.user.id, name=result.user.name, role=result.user.role)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    container: Annotated[Container, Depends(get_container)],
) -> Response:
    await run_in_threadpool(container.logout.execute, request.cookies[SESSION_COOKIE])
    response.status_code = 204
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=container.settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return response


@router.get("/me", response_model=MeOut)
def me(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[Session, Depends(current_session)],
) -> MeOut:
    return MeOut(id=user.id, name=user.name, role=user.role, csrf_token=session.csrf_token)
