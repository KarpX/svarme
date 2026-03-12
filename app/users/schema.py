from pydantic import BaseModel


class AdminLoginSchema(BaseModel):
    email: str
    password: str