import secrets

from aiohttp import web
from pydantic import ValidationError

from app.users.schema import AdminLoginSchema
from app.web.mw import SESSION_COOKIE


class AdminLoginView(web.View):
    async def post(self):
        try:
            data = await self.request.json()
            payload = AdminLoginSchema.model_validate(data)
        except ValidationError as e:
            return web.json_response({"error": e.errors()}, status=400)

        config = self.request.app.config.admin
        if payload.email != config.email or payload.password != config.password:
            return web.json_response({"error": "Invalid credentials"}, status=401)

        token = secrets.token_hex(32)
        self.request.app["admin_sessions"].add(token)

        response = web.json_response({"ok": True})
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="Strict")
        return response


class AdminLogoutView(web.View):
    async def post(self):
        token = self.request.cookies.get(SESSION_COOKIE)
        if token:
            self.request.app["admin_sessions"].discard(token)

        response = web.json_response({"ok": True})
        response.del_cookie(SESSION_COOKIE)
        return response
