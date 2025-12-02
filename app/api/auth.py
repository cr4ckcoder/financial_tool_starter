# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.domain import User, Company, UserRole
from app.schemas.user_schemas import UserCreate, UserRead, Token, AssignCompanyRequest
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

@router.get("/users", response_model=List[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Eagerly load the relationship to avoid MissingGreenlet error
    result = await db.execute(
        select(User).options(selectinload(User.assigned_companies))
    )
    return result.scalars().all()

@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Check if username exists
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 2. Create new user
    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        role=user.role.upper()
    )
    db.add(new_user)
    await db.commit()
    
    # 3. Re-fetch the user with eager loading
    # This replaces 'db.refresh' and ensures 'assigned_companies' is loaded
    # avoiding the MissingGreenlet error during response serialization.
    query = select(User).options(selectinload(User.assigned_companies)).where(User.id == new_user.id)
    result = await db.execute(query)
    created_user = result.scalars().first()
    
    return created_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user.id, 
        "role": user.role
    }

@router.post("/assign")
async def assign_company(
    payload: AssignCompanyRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Load user with their existing companies
    user_res = await db.execute(
        select(User)
        .options(selectinload(User.assigned_companies))
        .where(User.id == payload.user_id)
    )
    target_user = user_res.scalars().first()
    
    comp_res = await db.execute(select(Company).where(Company.id == payload.company_id))
    company = comp_res.scalars().first()
    
    if not target_user or not company:
        raise HTTPException(status_code=404, detail="User or Company not found")
    
    # Check if already assigned
    if company in target_user.assigned_companies:
        return {"status": "already_assigned", "user": target_user.username, "company": company.legal_name}

    target_user.assigned_companies.append(company)
    await db.commit()
    return {"status": "assigned", "user": target_user.username, "company": company.legal_name}