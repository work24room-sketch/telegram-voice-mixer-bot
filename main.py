import os
import uuid
import logging
import sys
import requests
import time
from urllib.parse import urljoin
import telebot
from flask import Flask, request, jsonify, send_file
from logging.handlers import RotatingFileHandler

# --- Настройка логирования ---
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.info("✅ Логирование настроено")

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # https://yourapp.onrender.com
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Telegram бота ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Обработчики Telegram ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logging.info(f"Команда /start от пользователя {message.from_user.id}")
    bot.reply_to(message, "🎵 Привет! Отправь мне голосовое сообщение, и я добавлю к нему фоновую музыку!")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    logging.info(f"Голосовое сообщение от пользователя {message.from_user.id}")
    bot.send_chat_action(message.chat.id, "typing")
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
        logging.info(f"Файл голосового сообщения: {file_url}")

        redirect_text = (
            "🎵 Спасибо за голосовое сообщение! \n\n"
            "Для обработки и микширования с музыкой, пожалуйста, "
            "воспользуйтесь нашим основным чат-ботом. \n\n"
            "Перейдите в @YourSaleBotName для продолжения работы 😊"
        )
        bot.reply_to(message, redirect_text)
        logging.info(f"Перенаправление отправлено пользователю {message.from_user.id}")
    except Exception as e:
        logging.error(f"Ошибка перенаправления: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке запроса")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    logging.info(f"Текстовое сообщение от пользователя {message.from_user.id}: {message.text}")
    bot.reply_to(message, "Отправьте мне голосовое сообщение 🎤")

# --- Функция очистки ---
def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logging.info(f"Файл удален: {filename}")
    except Exception as e:
        logging.error(f"Ошибка при удалении файла {filename}: {e}")

# --- Flask приложение ---
app = Flask(__name__)

# --- Эндпоинты ---
@app.route("/health")
def health_check():
    logging.info("Health check request")
    return jsonify({"status": "healthy", "service": "voice-mixer-api", "timestamp": time.time(), "version": "1.0"})

@app.route("/")
def index():
    logging.info("Root request")
    return "🎵 Voice Mixer Bot is running! Use /health for status check."

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    else:
        return "Invalid request", 403

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        logging.info("Process audio request")
        return jsonify({"status": "success", "message": "Audio processing endpoint"})
    except Exception as e:
        logging.error(f"Error in process_audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        logging.info(f"Download request for file: {filename}")
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading file {filename}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404

@app.route("/api/generate", methods=["POST"])
def generate_for_salebot():
    try:
        logging.info("API generate request from Salebot")
        data = request.get_json()
        if not data or 'voice_message_url' not in data:
            logging.warning("Missing voice_message_url in request")
            return jsonify({"status": "error", "message": "Missing required field: voice_message_url"}), 400

        client_id = data.get('client_id', 'unknown')
        name = data.get('name', 'Guest')
        voice_url = data['voice_message_url']

        logging.info(f"Processing audio for client: {client_id}, name: {name}")

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        response = requests.get(voice_url)
        if response.status_code != 200:
            logging.error(f"Failed to download voice message: {response.status_code}")
            return jsonify({"status": "error", "message": f"Failed to download voice message: {response.status_code}"}), 400

        with open(voice_filename, "wb") as f:
            f.write(response.content)
        logging.info(f"Voice message downloaded: {voice_filename}")

        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        logging.info("Starting audio processing...")
        # Функцию mix_voice_with_music нужно определить отдельно
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)
        logging.info("Audio processing completed")

        download_url = urljoin(request.host_url, f"download/{output_filename}")
        cleanup(voice_filename)

        logging.info(f"Audio ready for download: {download_url}")
        return jsonify({"status": "success", "message": "Audio mixed successfully",
                        "download_url": download_url, "filename": output_filename})

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Инициализация приложения ---
def create_app():
    setup_logging()
    logging.info("🚀 Приложение инициализировано!")
    # Устанавливаем webhook Telegram
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + "/webhook")
    logging.info(f"Webhook установлен: {WEBHOOK_URL}/webhook")
    return app

# --- Точка входа для Gunicorn ---
application = create_app()

if __name__ == "__main__":
    setup_logging()
    logging.info("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
