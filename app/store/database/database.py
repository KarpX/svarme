from typing import TYPE_CHECKING, Any

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.store.database.sqlalchemy_base import BaseModel

if TYPE_CHECKING:
    from app.web.app import Application

class Database:
    def __init__(self, app: "Application"):
        self.app = app
        self.engine: AsyncEngine = None
        self.sessionmaker: async_sessionmaker[AsyncSession] = None
        self.database = BaseModel

    async def connect(self, *args, **kwargs) -> None:
        config = self.app.config.database
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            database=config.database,
        )
        self.engine = create_async_engine(url, echo=True)
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def disconnect(self, *args, **kwargs) -> None:
        if self.engine:
            await self.engine.dispose()

