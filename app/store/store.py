import typing

from app.store.database.database import Database

if typing.TYPE_CHECKING:
    from app.web.app import Application


async def _on_startup(app: "Application"):
    await app.database.connect()
    await app.store.redis.connect(app)
    await app.store.rabbit.connect()
    await app.store.tg_api.connect()
    await app.store.bot.restore_timers()
    await app.store.rabbit.start_consuming(app.store.bot.handle_update)
    app.store.poller.start()

async def _on_cleanup(app: "Application"):
    await app.store.poller.stop()
    await app.store.rabbit.disconnect()
    await app.store.tg_api.disconnect()
    await app.store.redis.disconnect(app)
    await app.database.disconnect()

class Store:
    def __init__(self, app: "Application"):
        self.app = app
        from app.users.accessor import UserAccessor
        from app.store.tg_api.accessor import TgApiAccessor
        from app.store.bot.manager import BotManager
        from app.store.bot.poller import Poller

        from app.store.quiz.accessor import QuizAccessor
        from app.store.game.accessor import GameAccessor
        from app.store.rabbit.accessor import RabbitAccessor
        from app.store.redis.accessor import RedisAccessor

        self.quiz = QuizAccessor(self)
        self.game = GameAccessor(self)
        self.user = UserAccessor(self)
        self.tg_api = TgApiAccessor(app)
        self.bot = BotManager(app)
        self.poller = Poller(app)
        self.redis = RedisAccessor(app)
        self.rabbit = RabbitAccessor(app)

def setup_store(app: "Application") -> None:
    app.database = Database(app)
    app.store = Store(app)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)