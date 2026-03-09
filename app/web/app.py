from aiohttp import web
from aiohttp.web import (
    Application as AiohttpApplication,
)

from app.store.store import setup_store
from app.web.config import setup_config
from app.store.database.database import Database
from app.web.logger import setup_logging

from .routes import setup_routes

__all__ = ("Application",)


class Application(AiohttpApplication):
    config = "./config.yaml"
    store = None
    database = None


app = Application()


def setup_app(config_path: str) -> Application:
    setup_logging(app)
    setup_config(app, config_path)
    setup_routes(app)
    setup_store(app)

    # setup_middlewares(app)
    return app

if __name__ == "__main__":
    app = setup_app(app.config)
    web.run_app(app, port=8000)