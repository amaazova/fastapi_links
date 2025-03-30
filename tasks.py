import logging
import asyncio
from datetime import datetime, timedelta
from celery import Celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from config import DATABASE_URL_ASYNC, INACTIVE_DAYS_THRESHOLD, REDIS_URL
from models import Link

logger = logging.getLogger(__name__)
celery_app = Celery(__name__, broker=REDIS_URL)

async def _cleanup_expired_links():
    new_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True, future=True)
    NewSessionMaker = sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
    async with NewSessionMaker() as db:
        stmt = select(Link).filter(Link.expires_at != None, Link.expires_at < datetime.utcnow())
        result = await db.execute(stmt)
        expired_links = result.scalars().all()
        for link in expired_links:
            await db.delete(link)
        await db.commit()
        logger.info("Celery cleanup: %d expired links removed", len(expired_links))
    await new_engine.dispose()

@celery_app.task
def cleanup_expired_links_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup_expired_links())
    loop.close()

async def _cleanup_inactive_links():
    new_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True, future=True)
    NewSessionMaker = sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
    async with NewSessionMaker() as db:
        threshold_date = datetime.utcnow() - timedelta(days=INACTIVE_DAYS_THRESHOLD)
        stmt = select(Link).filter(
            ((Link.last_redirect_at != None) & (Link.last_redirect_at < threshold_date)) |
            ((Link.last_redirect_at == None) & (Link.created_at < threshold_date))
        )
        result = await db.execute(stmt)
        inactive_links = result.scalars().all()
        for link in inactive_links:
            await db.delete(link)
        await db.commit()
        logger.info("Celery inactive cleanup: %d inactive links removed", len(inactive_links))
    await new_engine.dispose()

@celery_app.task
def cleanup_inactive_links_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup_inactive_links())
    loop.close()
