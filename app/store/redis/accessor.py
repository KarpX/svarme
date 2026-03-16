from redis.asyncio import Redis

class RedisAccessor:
    def __init__(self, app):
        self.app = app
        self.store = self.app.store
        self.client: Redis | None = None

    async def connect(self, app):
        config = app.config.redis  # добавь redis в свой Config
        self.client = Redis(
            host=config.host,
            port=config.port,
            password=config.password,
            decode_responses=True
        )

    async def disconnect(self, app):
        if self.client:
            await self.client.close()

    async def set_limit(self, key: str, seconds: int) -> bool:
        # nx=True: установить только если не существует
        # ex=seconds: время жизни ключа
        res = await self.client.set(key, "1", ex=seconds, nx=True)
        return res is True or res == "OK"