# Базовый образ с полноценным Debian (не Alpine)
FROM python:3.13-slim-bullseye

# Обновляем пакеты и устанавливаем ffmpeg (для pydub)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Экспонируем порт (Render автоматически его подставит через $PORT)
ENV PORT=10000
EXPOSE $PORT

# Команда запуска
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:$PORT"]
