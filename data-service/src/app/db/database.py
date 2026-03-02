import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

database_url = str(os.environ.get('DATABASE_URL'))

engine = create_async_engine(database_url, echo=True)
new_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session

async def check_db_connection() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1))
        logging.info('Database connection successful')
        return True
    except Exception as e:
        logging.error(f'Database connection failed: {e}')
        return False
