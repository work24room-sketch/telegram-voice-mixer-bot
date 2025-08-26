from flask import Flask, request, jsonify, send_file
import os
import uuid
import time
import requests
import logging
import json  # ← ДОБАВЬТЕ ЭТОТ ИМПОРТ!
from audio_processor import mix_voice_with_music

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# ==================== ЭНДПОИНТЫ ====================

@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "voice-mixer-api",
        "timestamp": time.time(),
        "version": "1.0"
    })

@app.route("/")
def index():
    return "🎵 Voice Mixer Bot API is running! Use /health for status check."

@app.route("/process_audio", methods=["POST"])
def process_audio():
    """Основной эндпоинт для обработки аудио"""
    logger.info("🎯 /process_audio endpoint called!")
    
    try:
        # Безопасное получение JSON
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            data = request.get_json(force=True, silent=True) or {}
        
        logger.info(f"📦 JSON data: {json.dumps(data, ensure_ascii=False)}")

        # Извлекаем параметры
        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")
        chat_id = data.get("chat_id")

        logger.info(f"🔍 voice_url: {voice_url}")
        logger.info(f"🔍 client_id: {client_id}")
        logger.info(f"🔍 name: {name}")
        logger.info(f"🔍 chat_id: {chat_id}")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        if not chat_id and client_id:
            chat_id = client_id
            logger.info(f"🔧 Using client_id as chat_id: {chat_id}")

        if not chat_id:
            return jsonify({"error": "chat_id is required"}), 400

        # 1. Скачиваем голосовое сообщение
        logger.info(f"📥 Downloading from: {voice_url}")
        voice_response = requests.get(voice_url, timeout=30)
        voice_response.raise_for_status()

        # 2. Сохраняем временный файл
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # 3. Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        logger.info("🎵 Mixing audio with music...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # 4. Отправляем в Telegram
        logger.info("📤 Sending to Telegram...")
        with open(output_path, "rb") as audio_file:
            files = {'audio': audio_file}
            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
            send_data = {
                'chat_id': chat_id,
                'title': '🎵 Ваш микс!',
                'caption': f'Для {name}' if name else 'Ваш микс готов!'
            }
            send_response = requests.post(send_url, data=send_data, files=files, timeout=30)
            send_response.raise_for_status()
            result = send_response.json()
            ready_file_id = result['result']['audio']['file_id']

        # 5. Очистка
        cleanup(voice_filename)
        cleanup(output_path)

        # 6. Возвращаем ответ
        response_data = {
            "status": "success",
            "message": "Audio sent to Telegram successfully",
            "telegram_file_id": ready_file_id,
            "client_id": client_id,
            "name": name
        }
        
        logger.info(f"✅ Success response sent")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except:
        pass

if __name__ == "__main__":
    logger.info("🌐 Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
