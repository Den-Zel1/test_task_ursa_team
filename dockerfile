# Этап 1: Сборка и тесты
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS tester
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --all-extras --frozen
COPY . .
RUN uv run pytest

# Этап 2: Финальный образ
FROM python:3.13-slim
WORKDIR /app

# 1. Добавляем системные сертификаты для HTTPS запросов
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Достаем бинарники uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Копируем конфиги
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 2. КОПИРУЕМ ВСЁ (вместо только main.py), чтобы подтянулись все файлы и конфиги
COPY . .

EXPOSE 8000
# Используем --host 0.0.0.0, чтобы API было доступно снаружи контейнера
CMD ["uv", "run", "python", "main.py"]
