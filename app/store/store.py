import typing

from app.store.database.database import Database

if typing.TYPE_CHECKING:
    from app.web.app import Application


async def _on_startup(app: "Application"):
    await app.database.connect()
    await app.store.tg_api.connect()
    app.store.poller.start()

async def _on_cleanup(app: "Application"):
    await app.store.poller.stop()
    await app.store.tg_api.disconnect()
    await app.database.disconnect()

class Store:
    def __init__(self, app: "Application"):
        self.app = app
        from app.users.accessor import UserAccessor
        from app.store.tg_api.accessor import TgApiAccessor
        from app.store.bot.manager import BotManager
        from app.store.bot.poller import Poller

        from app.store.quiz.accessor import QuizAccessor

        self.quiz = QuizAccessor(self)
        self.user = UserAccessor(self)
        self.tg_api = TgApiAccessor(app)
        self.bot = BotManager(app)
        self.poller = Poller(app)

def setup_store(app: "Application") -> None:
    app.database = Database(app)
    app.store = Store(app)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)