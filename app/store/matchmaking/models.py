from sqlalchemy import Integer, BigInteger, ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.store.database.sqlalchemy_base import BaseModel as Base
from app.store.tg_api.game_constants import GameModes


class MatchmakingModel(Base):
    __tablename__ = "matchmaking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False, unique=True 
    )
    search_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    game_mode: Mapped[str] = mapped_column(String(50), nullable=False, default=GameModes.STANDART.value)
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )