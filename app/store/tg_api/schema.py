from pydantic import BaseModel, Field
from typing import Optional

class Chat(BaseModel):
    id: int

class Message(BaseModel):
    message_id: int
    chat: Chat
    text: Optional[str] = None

class CallbackQuery(BaseModel):
    id: str
    from_user: Chat = Field(..., alias="from")
    message: Optional[Message] = None
    data: str

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = None