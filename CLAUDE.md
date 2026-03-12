# Project: Jeopardy Bot (Pure aiohttp Stack)

## Tech Stack

- **Web/API:** aiohttp (Client & Server)
- **Broker:** RabbitMQ (aio-pika)
- **Database:** PostgreSQL + SQLAlchemy (Async)
- **Validation:** Pydantic v2
- **Environment:** Docker Compose

### Схема базы данных (Кратко)

- `user`: id (TG), game_id, points.
- `game`: status, current_round, question_asked_at, remaining_seconds, active_question_id.
- `question`: id, category_id, text, answer, price.
- `statistic`: user_id, games_played, wins, etc.
- `game_answered_questions`: трекинг использованных вопросов в сессии.

### Баги

- При быстром выборе категории пропало сообщение
