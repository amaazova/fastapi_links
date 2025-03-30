from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    links = relationship("Link", back_populates="owner")

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    redirect_count = Column(Integer, default=0, nullable=False)
    last_redirect_at = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    category = Column(String, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    owner = relationship("User", back_populates="links")
