# Добавьте этот импорт в начало файла
import requests
from urllib.parse import urljoin
import threading
from flask import Flask, request, jsonify, send_file
import telebot
import os
import uuid
import time  # Добавьте этот импорт
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Telegram бота ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Обработчики Telegram ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🎵 Привет! Отправь мне голосовое сообщение, и я добавлю к нему фоновую музыку!")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    try:
        print("🔊 Получено голосовое сообщение!")
        bot.send_chat_action(message.chat.id, "upload_audio")

        # Скачиваем голосовое сообщение
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(downloaded_file)

        # Обрабатываем аудио напрямую
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

# --- Функция очистки ---
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
        bot.remove_webhook()
        print("✅ Бот запущен и слушает сообщения...")
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"❌ Ошибка в работе бота: {e}")

# --- Инициализация Flask ---
app = Flask(__name__)

# --- Эндпоинты Flask ---
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "service": "voice-mixer-api", "timestamp": time.time(), "version": "1.0"})

@app.route("/")
def index():
    return "🎵 Voice Mixer Bot is running! Use /health for status check."

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        # Ваш код для обработки аудио через API
        return jsonify({"status": "success", "message": "Audio processing endpoint"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        # Проверяем безопасность пути
        if not os.path.exists(filename) or '..' in filename or '/' in filename:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        return send_file(filename, as_attachment=True, download_name=f"mixed_audio_{filename.split('_')[-1]}")
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404

@app.route("/api/generate", methods=["POST"])
def generate_for_salebot():
    try:
        # Получаем данные от Salebot
        data = request.get_json()
        
        # Проверяем обязательные поля
        if not data or 'voice_message_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: voice_message_url"
            }), 400
        
        client_id = data.get('client_id', 'unknown')
        name = data.get('name', 'Guest')
        voice_url = data['voice_message_url']
        
        print(f"🎵 Запрос от Salebot: client_id={client_id}, name={name}")
        
        # Скачиваем голосовое сообщение
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        
        response = requests.get(voice_url)
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"Failed to download voice message: {response.status_code}"
            }), 400
        
        with open(voice_filename, "wb") as f:
            f.write(response.content)
        
        # Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        print("🎵 Начинаем обработку аудио для Salebot...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)
        print("✅ Аудио обработано для Salebot!")
        
        # Формируем URL для скачивания
        download_url = urljoin(request.host_url, f"download/{output_filename}")
        
        # Очистка временных файлов (голосового сообщения)
        cleanup(voice_filename)
        
        return jsonify({
            "status": "success",
            "message": "Audio mixed successfully",
            "download_url": download_url,
            "filename": output_filename
        })
        
    except Exception as e:
        error_msg = f"❌ Error processing audio: {str(e)}"
        print(error_msg)
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 500

# --- Инициализация приложения ---
def create_app():
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        print("🚀 Приложение инициализировано!")
    return app

# --- Точка входа для Gunicorn ---
application = create_app()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    print("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
