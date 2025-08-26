from flask import Flask, request, jsonify, send_file
import os, uuid, time, requests, logging
from audio_processor import mix_voice_with_music

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- ЭНДПОИНТЫ ---
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

@app.route("/test", methods=["GET", "POST"])
def test_endpoint():
    logger.info("✅ Test request received")
    try:
        data = request.get_json()
        logger.info(f"📦 JSON data: {data}")
    except:
        logger.info("📦 No JSON data")
    return jsonify({"status": "test_ok", "message": "Request received"})

@app.route("/process_audio", methods=["POST"])
def process_audio():
    logger.info("🎯 /process_audio called")
    try:
        # Получение данных
        data = request.get_json(force=True, silent=True) or request.form.to_dict()
        if not data:
            return jsonify({"error": "No data received"}), 400

        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        logger.info(f"🔍 voice_url={voice_url}, client_id={client_id}, name={name}")

        # --- Скачиваем голосовое ---
        try:
            r = requests.get(voice_url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            return jsonify({"error": f"Failed to download voice: {str(e)}"}), 400

        voice_file = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_file, "wb") as f:
            f.write(r.content)
        logger.info(f"💾 Saved voice: {voice_file}")

        # --- Обрабатываем аудио ---
        output_file = f"mixed_{uuid.uuid4().hex}.mp3"
        try:
            mix_voice_with_music(voice_file, output_file, GITHUB_MUSIC_URL)
            logger.info("✅ Audio mixed successfully")
        except Exception as e:
            cleanup(voice_file)
            return jsonify({"error": f"Audio processing failed: {str(e)}"}), 500

        download_url = f"{request.host_url}download/{output_file}"
        cleanup(voice_file)

        response_data = {
            "status": "success",
            "message": "Audio processed successfully",
            "download_url": download_url,
            "file_name": output_file,
            "client_id": client_id,
            "name": name,
            "processed_at": time.time()
        }
        logger.info(f"✅ Success: {response_data}")

        # --- Отправка в SaleBot (опционально) ---
        if "telegram_api_key" in os.environ and "salebot_block_id" in os.environ and client_id:
            try:
                payload = {
                    "apiKey": os.environ.get("telegram_api_key"),
                    "client_id": client_id,
                    "name": name,
                    "file_url": download_url,
                    "status": "success",
                    "message": "Аудио готово 🎵"
                }
                sale_url = f"https://api.salebot.pro/v1/project/{os.environ.get('salebot_project_id')}/sendWebhook/{os.environ.get('salebot_block_id')}"
                r = requests.post(sale_url, json=payload)
                logger.info(f"📡 Pushed to SaleBot: {r.status_code} {r.text}")
            except Exception as e:
                logger.error(f"❌ SaleBot push failed: {str(e)}")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ /process_audio error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    path = os.path.join(os.getcwd(), filename)
    if os.path.exists(path):
        logger.info(f"📥 Serving file: {filename}")
        return send_file(path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

# --- Удаление временных файлов ---
def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"🗑️ Deleted: {filename}")
    except Exception as e:
        logger.error(f"⚠️ Cleanup failed: {filename}, {e}")

# --- Запуск сервера ---
if __name__ == "__main__":
    logger.info("🌐 Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
