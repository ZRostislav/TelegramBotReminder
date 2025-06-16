# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копируем весь код бота
COPY . .

# Устанавливаем переменную окружения для запуска
ENV BOT_TOKEN=your_token_here
ENV CHAT_ID=your_chat_id_here

# Запускаем бота
CMD ["python", "bot.py"]
