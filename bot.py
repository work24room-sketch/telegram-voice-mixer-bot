import telebot
import requests
import os
import uuid
from time import sleep

# Конфигурация
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Создадим переменную в Render
RENDER_SERVICE_URL = os.environ.get('RENDER_SERVICE_URL')  # URL вашего Flask-сервиса, например https://your-flask-service.onrender.com

# Инициализируем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Обрабатывает входящие голосовые сообщения"""
    try:
        # Отправляем статус "печатает..."
        bot.send_chat_action(message.chat.id, 'upload_audio')

        # Получаем информацию о файле
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Сохраняем файл локально с уникальным именем
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # 1. Отправляем файл на обработку на наш Flask-сервер
        process_url = f"{RENDER_SERVICE_URL}/process_audio"
        payload = {"voice_file_path": voice_filename}
        response = requests.post(process_url, json=payload)
        response.raise_for_status()
        result_data = response.json()
        result_filename = result_data['processed_file']

        # 2. Даем серверу время на создание файла
        sleep(5)

        # 3. Скачиваем готовый файл с сервера
        download_url = f"{RENDER_SERVICE_URL}/download/{result_filename}"
        mixed_audio_response = requests.get(download_url)
        mixed_audio_response.raise_for_status()

        # Сохраняем его временно, чтобы отправить
        with open(result_filename, 'wb') as f:
            f.write(mixed_audio_response.content)

        # 4. Отправляем готовый микс пользователю
        with open(result_filename, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file, title="Ваш микс!")

        # 5. Удаляем временные файлы
        cleanup(voice_filename)
        cleanup(result_filename)

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"Ошибка при обработке аудио на сервере: {e}")
        cleanup(voice_filename)
    except Exception as e:
        bot.reply_to(message, f"Произошла непредвиденная ошибка: {e}")
        cleanup(voice_filename)
        if 'result_filename' in locals():
            cleanup(result_filename)

def cleanup(filename):
    """Удаляет временный файл"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except:
        pass # Игнорируем ошибки удаления

# Запускаем бота
if __name__ == '__main__':
    bot.polling(none_stop=True)