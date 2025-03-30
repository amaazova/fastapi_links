from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, validator

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    category: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_public: Optional[bool] = None

    @validator("expires_at", pre=True, always=True)
    def parse_expires_at(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime):
            return v
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d"
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format for expires_at. Supported formats: {date_formats}")

class LinkOut(BaseModel):
    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]
    redirect_count: int
    last_redirect_at: Optional[datetime]
    owner_id: Optional[int]
    category: Optional[str] = None
    is_public: bool

    class Config:
        orm_mode = True
