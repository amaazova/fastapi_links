import random
import string
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Link

def generate_short_code(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def get_unique_short_code(db: AsyncSession, custom_alias: str = None) -> str:
    if custom_alias:
        if not custom_alias.isalnum():
            raise HTTPException(status_code=400, detail="Custom alias must be alphanumeric")
        stmt = select(Link).filter(Link.short_code == custom_alias)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Custom alias already exists")
        return custom_alias
    else:
        while True:
            code = generate_short_code()
            stmt = select(Link).filter(Link.short_code == code)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                return code
