import os
import uuid
import time
import requests
from flask import Flask, request, jsonify, send_file
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Flask ---
app = Flask(__name__)

# ==================== ЭНДПОИНТЫ ====================

@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "voice-mixer-api",
        "timestamp": time.time(),
    })

@app.route("/")
def index():
    return "🎵 Voice Mixer Bot API is running!"

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        print(f"📋 Content-Type: {request.content_type}")
        data = request.get_json(force=True, silent=True) or request.form.to_dict()
        print(f"📦 Received data: {data}")
        return jsonify({"status": "ok"})

        voice_file_url = data.get("voice_file_url")
        chat_id = data.get("chat_id")
        attachments_json = data.get("attachments_json")

        if not voice_file_url or not voice_file_url.startswith(("http://", "https://")):
            return jsonify({
                "status": "error",
                "message": f"Invalid or missing voice_file_url: {voice_file_url}",
                "voice_file_url": str(voice_file_url),
                "attachments_json": str(attachments_json)
            }), 400

        # --- Скачивание файла ---
        print(f"📥 Downloading from: {voice_file_url}")
        voice_response = requests.get(voice_file_url)
        voice_response.raise_for_status()

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # --- Микс ---
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        mix_voice_with_music(voice_filename, output_filename, GITHUB_MUSIC_URL)

        # --- Отправка в Telegram ---
        with open(output_filename, "rb") as audio_file:
            files = {"audio": audio_file}
            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
            send_data = {"chat_id": chat_id, "title": "🎵 Ваш микс!"}
            send_response = requests.post(send_url, data=send_data, files=files)
            send_response.raise_for_status()

        ready_file_id = send_response.json()["result"]["audio"]["file_id"]

        # --- Ответ ---
        return jsonify({
            "status": "success",
            "ready_file_id": ready_file_id,
            "voice_file_url": voice_file_url
        })

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
