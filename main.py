import threading
from flask import Flask, request, jsonify, send_file
import telebot
import os
import uuid
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Flask ---
app = Flask(__name__)

import time
from flask import jsonify

# Добавьте этот эндпоинт вместе с другими Flask-роутами
@app.route("/health")
def health_check():
    """Специальный эндпоинт для проверки работоспособности UptimeRobot"""
    return jsonify({
        "status": "healthy",
        "service": "voice-mixer-api",
        "timestamp": time.time(),
        "version": "1.0"
    })

@app.route("/")
def index():
    """Главная страница тоже подойдет для пинга"""
    return "🎵 Voice Mixer Bot is running! Use /health for status check."

# --- Инициализация Telegram бота ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Эндпоинты Flask ---
@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.get_json()
        voice_file_path = data.get("voice_file_path")

        if not voice_file_path or not os.path.exists(voice_file_path):
            return jsonify({"error": "File not found"}), 400

        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        result_path = mix_voice_with_music(voice_file_path, output_path, GITHUB_MUSIC_URL)
        return jsonify({"processed_file": output_filename})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Voice Mixer Bot is running!"

# --- Обработчики Telegram ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🎵 Привет! Отправь мне голосовое сообщение, и я добавлю к нему фоновую музыку!")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    try:
        print("🔊 Получено голосовое сообщение!")  # Логирование
        bot.send_chat_action(message.chat.id, "upload_audio")

        # Скачиваем голосовое сообщение
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(downloaded_file)

        # Обрабатываем аудио напрямую (без HTTP запросов)
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        print("🎵 Начинаем обработку аудио...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)
        print("✅ Аудио обработано!")

        # Отправляем результат пользователю
        with open(output_path, "rb") as audio_file:
            bot.send_audio(message.chat.id, audio_file, title="Ваш микс!", performer="Voice Mixer Bot")

        # Очистка временных файлов
        cleanup(voice_filename)
        cleanup(output_path)
        print("🗑️ Временные файлы удалены")

    except Exception as e:
        error_msg = f"❌ Произошла ошибка: {str(e)}"
        print(error_msg)
        bot.reply_to(message, error_msg)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "Отправьте мне голосовое сообщение 🎤")

def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"⚠️ Ошибка при удалении файла {filename}: {e}")

# --- Запуск бота в отдельном потоке ---
def run_bot():
    print("🤖 Запускаем Telegram-бота...")
    try:
        bot.remove_webhook()  # Важно: отключаем вебхуки если они были
        print("✅ Бот запущен и слушает сообщения...")
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"❌ Ошибка в работе бота: {e}")

# --- Инициализация приложения ---
def create_app():
    # Запускаем бота только при непосредственном запуске (не в Gunicorn)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        print("🚀 Приложение инициализировано!")
    
    return app

# --- Точка входа для Gunicorn ---
application = create_app()

if __name__ == "__main__":
    # Для локального запуска
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
