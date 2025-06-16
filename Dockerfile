# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости, включая Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libffi-dev \
    python3-dev \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем исходный код
COPY . .

# Указываем команду по умолчанию (если твой скрипт называется bot.py)
CMD ["python", "bot.py"]
