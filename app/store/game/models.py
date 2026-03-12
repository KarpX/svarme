from typing import Optional
from sqlalchemy import Integer, String, BigInteger, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.store.database.sqlalchemy_base import BaseModel as Base


class UserModel(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    game_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("game.id", ondelete="SET NULL"), nullable=True)
    points: Mapped[int] = mapped_column(default=0)

    statistic: Mapped["StatisticModel"] = relationship(back_populates="user", uselist=False)


class StatisticModel(Base):
    __tablename__ = "statistic"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    games_played: Mapped[int] = mapped_column(default=0)
    max_points: Mapped[int] = mapped_column(default=0)
    right_answers: Mapped[int] = mapped_column(default=0)
    wins: Mapped[int] = mapped_column(default=0)

    user: Mapped["UserModel"] = relationship(back_populates="statistic")


class GameModel(Base):
    __tablename__ = "game"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    game_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="waiting")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    current_round: Mapped[int] = mapped_column(Integer, default=1)

    choosing_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    target_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    active_question_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    question_asked_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    remaining_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    current_highest_bet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class GameCategoriesModel(Base):
    __tablename__ = "game_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("category.id", ondelete="CASCADE"), nullable=False)


class GameAnsweredQuestionsModel(Base):
    __tablename__ = "game_answered_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id", ondelete="CASCADE"), nullable=False)


class GameFinalBetsModel(Base):
    __tablename__ = "game_final_bets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    bet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)
