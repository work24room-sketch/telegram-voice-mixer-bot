import threading
from flask import Flask, request, jsonify, send_file
import os
import uuid
import time
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Flask ---
app = Flask(__name__)

# ==================== ЭНДПОИНТЫ ====================
@app.route("/health")
def health_check():
    """Эндпоинт для проверки работоспособности"""
    return jsonify({
        "status": "healthy",
        "service": "voice-mixer-api",
        "timestamp": time.time(),
        "version": "1.0"
    })

@app.route("/")
def index():
    """Главная страница"""
    return "🎵 Voice Mixer Bot API is running! Use /health for status check."

@app.route("/process_audio", methods=["POST"])
def process_audio():
    """Основной эндпоинт для обработки аудио"""
    try:
        data = request.get_json()
        voice_file_id = data.get("voice_file_id")
        chat_id = data.get("chat_id")
        
        if not voice_file_id or not chat_id:
            return jsonify({"status": "error", "message": "Missing required parameters"}), 400

        # Здесь будет ваш код обработки аудио
        # Пока возвращаем заглушку для теста
        return jsonify({
            "status": "success", 
            "message": "Audio processing endpoint ready",
            "voice_file_id": voice_file_id,
            "chat_id": chat_id
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== ЗАПУСК СЕРВЕРА ====================
if __name__ == "__main__":
    print("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
