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

# Папка для готовых файлов
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
        data = request.json
        print("📋 Content-Type:", request.content_type)
        print("📦 Received data:", data)

        voice_file_url = data.get("voice_file_url")
        voice_file_id = data.get("voice_file_id")
        chat_id = data.get("chat_id")

        if not (voice_file_url or voice_file_id) or not chat_id:
            return jsonify({"status": "error", "message": "Missing voice_file or chat_id"}), 400

        # --- Скачивание файла ---
        input_filename = f"voice_{uuid.uuid4().hex}.ogg"

        if voice_file_url:
            # Прямой URL
            print(f"📥 Downloading from URL: {voice_file_url}")
            resp = requests.get(voice_file_url)
            resp.raise_for_status()
            with open(input_filename, "wb") as f:
                f.write(resp.content)

        elif voice_file_id:
            # Получаем file_path через Telegram API
            print(f"📥 Downloading from Telegram by file_id: {voice_file_id}")
            file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
            r = requests.post(file_info_url, json={"file_id": voice_file_id})
            r.raise_for_status()
            file_path = r.json()["result"]["file_path"]

            file_download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            print(f"📥 Resolved Telegram file URL: {file_download_url}")

            resp = requests.get(file_download_url)
            resp.raise_for_status()
            with open(input_filename, "wb") as f:
                f.write(resp.content)

        # --- Микс ---
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)

        mix_voice_with_music(input_filename, output_path, GITHUB_MUSIC_URL)

        # --- Возвращаем ссылку ---
        mix_result_url = f"https://voice-mixer-bot.onrender.com/download/{output_filename}"

        return jsonify({
            "status": "success",
            "mix_result": mix_result_url
        }), 200

    except Exception as e:
        print("❌ Error in /process_audio:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


# Эндпоинт для скачивания готовых файлов
@app.route("/download/<filename>")
def download_file(filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"status": "error", "message": "File not found"}), 404
