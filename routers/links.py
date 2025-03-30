import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import io
import qrcode
from datetime import datetime

from schemas import LinkCreate, LinkOut
from models import Link
from auth import get_current_user, get_optional_current_user
from database import get_db
from utils import get_unique_short_code

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/shorten", response_model=LinkOut)
async def create_link(link: LinkCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    short_code = await get_unique_short_code(db, link.custom_alias)
    is_public = link.is_public if link.is_public is not None else False
    new_link = Link(
        original_url=str(link.original_url),
        short_code=short_code,
        expires_at=link.expires_at,
        owner_id=current_user.id,
        category=link.category,
        is_public=is_public
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    logger.info("Link created by %s: %s", current_user.username, new_link.short_code)
    return new_link

@router.post("/shorten/public", response_model=LinkOut)
async def create_link_public(link: LinkCreate, db: AsyncSession = Depends(get_db)):
    short_code = await get_unique_short_code(db, link.custom_alias)
    new_link = Link(
        original_url=str(link.original_url),
        short_code=short_code,
        expires_at=link.expires_at,
        owner_id=None,
        category=link.category,
        is_public=True
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    logger.info("Public link created: %s", new_link.short_code)
    return new_link

@router.get("/search", response_model=List[LinkOut])
async def search_links(query: str, skip: int = Query(0, ge=0), limit: int = Query(10, gt=0),
                       current_user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    if current_user:
        stmt = select(Link).filter(
            ((Link.is_public == True) | (Link.owner_id == current_user.id)),
            ((Link.original_url.ilike(f"%{query}%")) | (Link.short_code.ilike(f"%{query}%")))
        ).offset(skip).limit(limit)
    else:
        stmt = select(Link).filter(
            (Link.is_public == True),
            ((Link.original_url.ilike(f"%{query}%")) | (Link.short_code.ilike(f"%{query}%")))
        ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    logger.info("Searched links with query: '%s'", query)
    return result.scalars().all()

@router.get("/category/{category}", response_model=List[LinkOut])
async def get_links_by_category(category: str, current_user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    if current_user:
        stmt = select(Link).filter(
            ((Link.is_public == True) | (Link.owner_id == current_user.id)),
            (Link.category == category)
        )
    else:
        stmt = select(Link).filter(
            (Link.is_public == True),
            (Link.category == category)
        )
    result = await db.execute(stmt)
    logger.info("Fetched links for category: %s", category)
    return result.scalars().all()

@router.get("/{short_code}/stats", response_model=LinkOut)
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Link).filter(Link.short_code == short_code)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    logger.info("Fetched stats for link: %s", short_code)
    return link

@router.get("/{short_code}/qrcode")
async def get_qrcode(short_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(Link).filter(Link.short_code == short_code)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    short_url = request.url_for("redirect_link", short_code=link.short_code)
    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    logger.info("Generated QR code for link: %s", short_code)
    return StreamingResponse(buf, media_type="image/png")

@router.put("/{short_code}", response_model=LinkOut)
async def update_link(short_code: str, link_data: LinkCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    stmt = select(Link).filter(Link.short_code == short_code)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")
    link.original_url = str(link_data.original_url)
    link.expires_at = link_data.expires_at
    link.category = link_data.category
    if link_data.custom_alias and link_data.custom_alias != link.short_code:
        if not link_data.custom_alias.isalnum():
            raise HTTPException(status_code=400, detail="Custom alias must be alphanumeric")
        stmt = select(Link).filter(Link.short_code == link_data.custom_alias)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Custom alias already exists")
        link.short_code = link_data.custom_alias
    await db.commit()
    await db.refresh(link)
    try:
        from main import redis_client
        await redis_client.delete(f"short_code:{short_code}")
    except Exception:
        pass
    logger.info("Link updated by %s: %s", current_user.username, link.short_code)
    return link

@router.delete("/{short_code}")
async def delete_link(short_code: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    stmt = select(Link).filter(Link.short_code == short_code)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")
    await db.delete(link)
    await db.commit()
    try:
        from main import redis_client
        await redis_client.delete(f"short_code:{short_code}")
    except Exception:
        pass
    logger.info("Link deleted by %s: %s", current_user.username, short_code)
    return {"message": "Link deleted"}

@router.get("/{short_code}", name="redirect_link")
async def redirect_link(short_code: str, db: AsyncSession = Depends(get_db)):
    from main import redis_client  
    cache_key = f"short_code:{short_code}"
    try:
        cached_data = await redis_client.get(cache_key)
    except Exception:
        cached_data = None
    if cached_data:
        try:
            link_id_str, original_url = cached_data.decode("utf-8").split("|", 1)
            link_id = int(link_id_str)
        except Exception:
            stmt = select(Link).filter(Link.short_code == short_code)
            result = await db.execute(stmt)
            link = result.scalar_one_or_none()
            if not link:
                raise HTTPException(status_code=404, detail="Link not found")
            original_url = link.original_url
            link_id = link.id
    else:
        stmt = select(Link).filter(Link.short_code == short_code)
        result = await db.execute(stmt)
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        if link.expires_at and datetime.utcnow() > link.expires_at:
            await db.delete(link)
            await db.commit()
            raise HTTPException(status_code=410, detail="Link expired")
        original_url = link.original_url
        link_id = link.id
        try:
            await redis_client.setex(cache_key, 60, f"{link_id}|{original_url}")
        except Exception:
            pass
    stmt = select(Link).filter(Link.id == link_id)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.expires_at and datetime.utcnow() > link.expires_at:
        await db.delete(link)
        await db.commit()
        raise HTTPException(status_code=410, detail="Link expired")
    link.redirect_count += 1
    link.last_redirect_at = datetime.utcnow()
    await db.commit()
    logger.info("Redirected link %s, new count: %d", short_code, link.redirect_count)
    return RedirectResponse(url=original_url)
