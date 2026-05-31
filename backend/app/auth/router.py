from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserCreateResponse,
    UserResponse,
)
from app.auth.security import create_access_token
from app.auth.service import (
    activate_user_account,
    authenticate_user,
    change_password,
    create_user,
    deactivate_user_account,
    get_user_by_email,
    purge_user_profile,
    send_forgot_password_email,
)
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for_user(user: User) -> TokenResponse:
    token = create_access_token(subject=user.email, role=user.role.value)
    return TokenResponse(
        access_token=token,
        must_change_password=user.must_change_password,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_for_user(user)


@router.post("/login/json", response_model=TokenResponse)
def login_json(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_for_user(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post("/change-password", response_model=UserResponse)
def update_password(
    body: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        change_password(db, current_user, body.current_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    # Respond generically to avoid account enumeration.
    send_forgot_password_email(db, body.email)
    return {"detail": "If the account exists, a temporary password has been sent to email."}


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from sqlalchemy import select

    users = db.scalars(
        select(User).where(User.profile_removed.is_(False)).order_by(User.id)
    ).all()
    return users


@router.post("/users", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    if get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user, email_sent = create_user(
        db,
        body.email,
        body.full_name,
        body.password,
        body.role,
        send_welcome_email=body.send_welcome_email,
    )
    return UserCreateResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        welcome_email_sent=email_sent,
    )


@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        deactivate_user_account(db, user_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/users/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
def activate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        activate_user_account(db, user_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_profile(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        purge_user_profile(db, user_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
