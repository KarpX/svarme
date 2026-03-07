from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.store.database.database import Base

class UserModel(Base):
    __tablename__ = "user"

    id = Column(BigInteger, unique=True, primary_key=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="SET NULL"), nullable=True)
    points = Column(Integer, default=0)

    statistic = relationship("StatisticModel", uselist=False, back_populates="user")

class StatisticModel(Base):
    __tablename__ = "statistic"

    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    games_played = Column(Integer, default=0)
    max_points = Column(Integer, default=0)
    right_answers = Column(Integer, default=0)
    wins = Column(Integer, default=0)

    user = relationship("UserModel", back_populates="statistic")

class GameModel(Base):
    __tablename__ = "game"

    id = Column(BigInteger, primary_key=True)
    game_mode = Column(String(50), nullable=False)
    game_type = Column(String(50), nullable=False)
    status = Column(String(20), default="waiting")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    current_round = Column(Integer, default=1)

    choosing_user_id = Column(BigInteger, nullable=True)
    target_user_id = Column(BigInteger, nullable=True)
    active_question_id = Column(Integer, nullable=True)

    question_asked_at = Column(DateTime(timezone=True), nullable=True)
    remaining_seconds = Column(Integer, nullable=True)

    current_highest_bet = Column(Integer, nullable=True)