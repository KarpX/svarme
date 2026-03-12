from pydantic import BaseModel, Field

class Chat(BaseModel):
    id: int
    type: str = "group"

class TgUser(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_user: TgUser | None = Field(None, alias="from")
    text: str | None = None

    model_config = {"populate_by_name": True}

class CallbackQuery(BaseModel):
    id: str
    from_user: TgUser = Field(..., alias="from")
    message: Message | None = None
    data: str

class Update(BaseModel):
    update_id: int
    message: Message | None = None
    callback_query: CallbackQuery | None = None