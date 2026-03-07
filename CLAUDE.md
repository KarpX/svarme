# Идея проекта

Создание телеграм-бота "Своя игра"

# Базовые требования к игре

Возможность управлять ботом должен иметь каждый участник беседы. Минимальный набор команд к боту из чата:

1. Начать игру. Если идет сессия, начать новую нельзя.
2. Остановить игру. При остановке должно произойти досрочное завершение игры и выведены результаты.
3. Информация об игровой сессии. Бот должен выводить информацию о проведении конкурса. После завершения игры может выводиться информация о крайнем конкурсе.

# Задачи

1. Обязательные
   - Реализовать чат-бота в социальной сети
   - Реализовать механику. Бот должен поддерживать несколько бесед
   - Реализовать API администратора
   - Все состояния пользователей и игровых сессий должны храниться в СУБД Postgres
2. Дополнительные
   - Покрыть тестами основную механику
   - Покрыть тестами Admin API
   - Любые улучшения и усложнение процесса игры приветствуются
   - Каждый микросервис приложения должен быть запущен в своем собственном Docker-контейнере. Для воспроизводимости сборки напишите файл docker-compose.yml
   - Разделить этапы получения сообщений из Telegram и саму логику приложения, используя брокер сообщений, например RabbitMQ для повышения отказоустойчивости всего приложения.
   - Бот должен уметь переживать рестарт сервиса
   - Если процесс останавливается и перезапускается во время игровых сессий, он должен продолжиться с того момента, где прервался. Все таймеры и отложенные события должны возобновиться
   - Проект должен быть развернут на виртуальной машине в интернете с помощью docker-compose up. Образы должны скачиваться из внешнего registry. Их можно запушить в https://hub.docker.com или в Github — https://github.com/features/packages
   - Автоматически собирать образы проекта через Github Actions при push в репозиторий и раскладывать на удаленной машине
   - Покрыть тестами бота

# Схема базы данных

Table user {
id bigint [primary key] // TG-ID
game_id bigint
points integer
}

Table statistic {
user_id bigint [primary key]
games_played integer
max_points integer
right_answers integer
wins integer
}

Table game {
id bigint [primary key]
game_mode varchar // Быстрая / обычная
game_type varchar // В групповом чате / в личке
status varchar
created_at timestamp
current_round integer [default: 1]
choosing_user_id bigint
question_asked_at timestamp // Для жёсткого таймера
remaining_seconds integer // Для продолжения таймера
active_question_id integer
target_user_id bigint
current_highest_bet integer
}

Table category {
id integer [primary key]
name varchar
round integer // Номер раунда
}

Table question {
id integer [primary key]
category_id integer [ref: > category.id]
text text
answer varchar
price integer
}

Table game_categories {
id integer [primary key]
game_id bigint [ref: > game.id]
category_id integer [ref: > category.id]
}

Table game_answered_questions {
id integer [primary key]
game_id bigint [ref: > game.id]
question_id integer [ref: > question.id]
}

Table game_final_bets {
id integer [primary key]
game_id bigint [ref: > game.id]
user_id bigint [ref: > user.id]
bet integer
is_ready bool
}

Ref: statistic.user_id - user.id

Ref: game.id < user.game_id

# Структура проекта

app/
├── web/
│ ├── app.py # Application, setup_app(), on_startup/cleanup
│ ├── config.py # Загрузка config.yaml (bot_token, db.url, admin)
│ ├── routes.py # Регистрация всех роутов
│ └── mw.py # Auth middleware, error handler
├── store/
│ ├── store.py # Store — accessor'ы: quiz, game, tg_api, bot
│ ├── database/
│ │ └── database.py # AsyncEngine, Base, on_startup/cleanup
│ ├── tg_api/
│ │ ├── accessor.py # HTTP-клиент: send_message, answer_callback, edit_message
│ │ └── dataclasses.py # Update, Message, Chat, User, CallbackQuery
│ ├── bot/
│ │ ├── manager.py # BotManager.handle_update() — диспетчер состояний
│ │ └── poller.py # Poller: asyncio.Task, long-poll getUpdates → manager
│ ├── quiz/
│ │ ├── models.py # SQLAlchemy: Category, Question
│ │ └── accessor.py # CRUD категорий и вопросов
│ └── game/
│ ├── models.py # SQLAlchemy: Lobby, User, Statistic, + связи
│ └── accessor.py # CRUD лобби, игроков, ставок
├── quiz/
│ ├── views.py / routes.py / schema.py # Admin API: категории, вопросы
├── game/
│ ├── views.py / routes.py / schema.py # Admin API: лобби, статистика
└── users/
├── views.py / routes.py / schema.py # Auth (admin login/logout)
