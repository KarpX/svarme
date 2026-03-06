import typing

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.users.accessor import UserAccessor

        self.user = UserAccessor(self)

def setup_store(app: "Application") -> None:
    app.store = Store(app)