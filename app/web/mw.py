from aiohttp import web
from aiohttp.abc import Request

SESSION_COOKIE = "ADMIN_SESSION"
_EXCLUDED_PATHS = {"/admin/login", "/admin/logout"}


@web.middleware
async def auth_middleware(request: Request, handler):
    if request.path.startswith("/admin/") and request.path not in _EXCLUDED_PATHS:
        token = request.cookies.get(SESSION_COOKIE)
        if not token or token not in request.app.get("admin_sessions", set()):
            return web.json_response({"error": "Unauthorized"}, status=401)
    return await handler(request)