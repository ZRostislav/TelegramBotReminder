FROM python:3.12-slim

# Устанавливаем системные зависимости, включая Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libffi-dev \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей проекта
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Запуск
CMD ["python", "bot.py"]
