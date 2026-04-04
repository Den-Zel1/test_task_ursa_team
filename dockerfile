# Этап 1: Сборка и тесты
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS tester

WORKDIR /app

# Копируем конфигурацию и замок зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем всё (включая pytest, respx) в строгом режиме
RUN uv sync --all-extras --frozen

# Копируем остальной код (включая папку tests)
COPY . .

# ЗАПУСК ТЕСТОВ: Если они упадут, сборка здесь прервется
RUN uv run pytest


# Этап 2: Финальный образ для работы
FROM python:3.13-slim

WORKDIR /app

# Достаем бинарники uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Копируем только конфиги для установки продакшен-пакетов
COPY pyproject.toml uv.lock ./

# Ставим только рабочие зависимости (FastAPI, httpx и др.) без dev-пакетов
RUN uv sync --no-dev --frozen

# Копируем только исполняемый файл
COPY main.py .

EXPOSE 8000
CMD ["uv", "run", "python", "main.py"]
