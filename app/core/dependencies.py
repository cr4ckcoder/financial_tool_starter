# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select

from app.core.config import settings
from app.core.security import SECRET_KEY, ALGORITHM
from app.models.domain import User

# DB Setup
engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Eager load assigned_companies so we can check permissions easily later
    result = await db.execute(
        select(User)
        .options(selectinload(User.assigned_companies))
        .where(User.username == username)
    )
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user