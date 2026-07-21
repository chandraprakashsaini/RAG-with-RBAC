from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    get_password_hash_async,
    verify_password_or_dummy_async,
)
from app.db.connection import AsyncSessionLocal, get_db
from app.db.models import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

# Separate user management router
user_router = APIRouter(prefix="/users", tags=["users"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_id: UUID


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role_id: UUID
    role: str | None = None
    is_active: bool
    created_at: str
    updated_at: str


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: str


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == body.email).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    password_ok = await verify_password_or_dummy_async(
        body.password, user.password_hash if user else None
    )
    if not user or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role.name,
    )

    return LoginResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_id=user.role_id,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        ),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    result = await db.execute(select(UserRole).where(UserRole.id == request.role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    user = User(
        email=request.email,
        full_name=request.full_name,
        password_hash=await get_password_hash_async(request.password),
        role_id=request.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_id=user.role_id,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    # Fetch full user details including role_id and timestamps
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.db.models import User
        result = await db.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_id=user.role_id,
            role=current_user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(select(UserRole).where(UserRole.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists",
        )

    role = UserRole(name=request.name, description=request.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        created_at=role.created_at.isoformat(),
    )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(select(UserRole))
    roles = result.scalars().all()
    return [
        RoleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            created_at=r.created_at.isoformat(),
        )
        for r in roles
    ]


# ── User management routes ──────────────────────────────────────────────


class UserListEntry(BaseModel):
    id: UUID
    email: str
    full_name: str
    role_name: str
    role_id: UUID
    is_active: bool
    created_at: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


@user_router.get("", response_model=List[UserListEntry])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        UserListEntry(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_name=u.role.name,
            role_id=u.role_id,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_id=user.role_id,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@user_router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.full_name is not None:
        user.full_name = request.full_name
    if request.role_id is not None:
        role_result = await db.execute(select(UserRole).where(UserRole.id == request.role_id))
        if not role_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role_id = request.role_id
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.password is not None:
        user.password_hash = await get_password_hash_async(request.password)

    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_id=user.role_id,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@user_router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"deleted": True, "user_id": str(user_id)}