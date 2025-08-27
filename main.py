from flask import Flask, request, jsonify, send_file
import os
import uuid
import time
import requests
import logging
from audio_processor import mix_voice_with_music
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")  # ID таблицы в Google Sheets
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "google-credentials.json")

# --- Google Sheets клиент ---
def get_gsheet_client():
    """Создает клиента для работы с Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client

def append_to_google_sheet(row_data):
    """Добавляет строку в Google Таблицу"""
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1  # первая вкладка
        sheet.append_row(row_data, value_input_option="RAW")
        logger.info(f"✅ Записано в Google Sheets: {row_data}")
    except Exception as e:
        logger.error(f"❌ Ошибка записи в Google Sheets: {e}")

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
    logger.info("🎯 /process_audio endpoint called!")

    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict()
        if not data:
            return jsonify({"error": "No data received"}), 400

        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        logger.info(f"🔍 voice_url: {voice_url}")
        logger.info(f"🔍 client_id: {client_id}")
        logger.info(f"🔍 name: {name}")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        # Скачиваем голосовое сообщение
        logger.info(f"📥 Downloading from: {voice_url}")
        voice_response = requests.get(voice_url, timeout=30)
        voice_response.raise_for_status()

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)
        logger.info(f"💾 Saved voice as: {voice_filename}")

        # Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        logger.info("🎵 Mixing audio with music...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)
        logger.info("✅ Audio mixed successfully")

        # Формируем ссылку
        download_url = f"{request.host_url}download/{output_filename}"
        logger.info(f"🔗 Download URL: {download_url}")

        cleanup(voice_filename)

        response_data = {
    "status": "success",
    "mix_url": download_url,
    "client_id": client_id,
    "message": "Audio processed successfully"
}
        
return jsonify(response_data)

        # === Запись в Google Sheets ===
        append_to_google_sheet([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            client_id or "",
            name or "",
            voice_url,
            download_url
        ])

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Error in /process_audio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            logger.info(f"📥 Serving file: {filename}")
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"🗑️ Deleted: {filename}")
    except Exception as e:
        logger.error(f"⚠️ Cleanup error for {filename}: {e}")

# ==================== ЗАПУСК СЕРВЕРА ====================
if __name__ == "__main__":
    logger.info("🌐 Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
