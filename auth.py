import jwt
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from database import get_db
from models import User

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
bearer_scheme = HTTPBearer(description="Use 'Bearer <token>' to authenticate for refresh token.")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None, token_type: str = "access"):
    to_encode = data.copy()
    to_encode.update({"type": token_type})
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    if not expires_delta:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(data, expires_delta, token_type="refresh")

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        logger.error("JWT decode error: %s", e)
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing")
    payload = decode_access_token(token)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    stmt = select(User).filter(User.username == payload.get("sub"))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_current_user_bearer(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    stmt = select(User).filter(User.username == payload.get("sub"))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_optional_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        if token:
            return await get_current_user(token, db)
        return None
    except HTTPException:
        return None
