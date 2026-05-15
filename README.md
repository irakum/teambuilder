# TeamBuilder

Веб-застосунок для рівномірного розподілу учасників у команди
з урахуванням їх навичок та сумісності.

## Структура проєкту

```
teambuilder/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routers/        # FastAPI роутери (sessions, participants, ...)
│   │   ├── core/
│   │   │   └── config.py       # Налаштування через pydantic-settings
│   │   ├── db/
│   │   │   └── session.py      # Підключення до БД, Base, get_db()
│   │   ├── models/             # SQLAlchemy ORM моделі
│   │   ├── repositories/       # Шар доступу до даних (CRUD)
│   │   ├── schemas/            # Pydantic схеми (request / response)
│   │   ├── services/           # Бізнес-логіка
│   │   └── main.py             # Точка входу FastAPI
│   ├── alembic/                # Міграції БД
│   ├── tests/                  # pytest тести
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/                # Axios-клієнт і типи запитів
│       ├── components/         # React компоненти
│       ├── pages/              # Сторінки застосунку
│       └── types/              # TypeScript інтерфейси
├── nginx/                      # nginx конфіг для production
├── docker-compose.yml
└── .env.example
```

## Швидкий старт

```bash
# 1. Клонуй репозиторій і перейди до папки
git clone <repo> && cd teambuilder

# 2. Створи .env з прикладу
cp .env.example .env

# 3. Запусти всі сервіси
docker compose up --build

# 4. Виконай міграції (в окремому терміналі)
docker compose exec backend alembic upgrade head

# API доступне на:  http://localhost:8000/api/docs
# Frontend:         http://localhost:5173
```

## Корисні команди

```bash
# Створити нову міграцію після зміни моделей
docker compose exec backend alembic revision --autogenerate -m "add skill weights"

# Запустити тести
docker compose exec backend pytest -v

# Підключитись до БД
docker compose exec db psql -U postgres -d teambuilder
```
