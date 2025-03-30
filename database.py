from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL_ASYNC

async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True, future=True)
async_session_maker = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_models():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session_maker() as session:
        yield session