# Используем Python
FROM python:3.11

# Рабочая папка
WORKDIR /app

# Скопировать зависимости
COPY requirements.txt .

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код
COPY . .

# Запуск бота
CMD ["python", "bot.py"]
