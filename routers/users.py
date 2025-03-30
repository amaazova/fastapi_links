import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from models import User
from schemas import UserCreate, UserOut, Token, RefreshTokenRequest
from auth import get_password_hash, verify_password, create_access_token, create_refresh_token, get_current_user, decode_access_token
from database import get_db
from config import ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.username == user.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = User(username=user.username, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("User registered: %s", new_user.username)
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": user.username}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token({"sub": user.username})
    logger.info("User logged in: %s", user.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/token/refresh", response_model=Token)
async def refresh_access_token(refresh_req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(refresh_req.refresh_token)
    if payload is None or payload.get("type") != "refresh" or payload.get("sub") is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    stmt = select(User).filter(User.username == payload.get("sub"))
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=401, detail="User not found")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": payload.get("sub")}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token({"sub": payload.get("sub")})
    logger.info("Token refreshed for user: %s", payload.get("sub"))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/links", response_model=list)
async def get_user_links(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from models import Link
    stmt = select(Link).filter(Link.owner_id == current_user.id)
    result = await db.execute(stmt)
    logger.info("Fetched links for user: %s", current_user.username)
    return result.scalars().all()
