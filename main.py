from flask import Flask, request, jsonify, send_file
import os
import uuid
import time
import requests
import logging
from audio_processor import mix_voice_with_music

# === для очистки голоса ===
import torch
import torchaudio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# Загружаем модель шумоподавления один раз при старте
logger.info("📥 Loading denoiser model...")
try:
    denoise_model = torch.hub.load("facebookresearch/denoiser", "dns64")
    denoise_model.eval()
    logger.info("✅ Denoiser model loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load denoiser model: {e}")
    denoise_model = None

def denoise_audio(input_path, output_path):
    """Очистка аудио от шумов через pretrained модель"""
    if denoise_model is None:
        logger.warning("⚠️ Denoiser model not available, skipping denoise step")
        return input_path

    wav, sr = torchaudio.load(input_path)
    logger.info(f"🎙️ Loaded audio for denoising: {input_path}, sr={sr}")

    with torch.no_grad():
        denoised = denoise_model(wav.unsqueeze(0))[0]

    torchaudio.save(output_path, denoised.cpu(), sr)
    logger.info(f"✨ Denoised audio saved: {output_path}")
    return output_path

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
        logger.info(f"📦 Data: {data}")

        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        # 1. Скачиваем голосовое сообщение
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        logger.info(f"📥 Downloading from: {voice_url}")
        voice_response = requests.get(voice_url, timeout=30)
        voice_response.raise_for_status()
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)
        logger.info(f"💾 Saved voice as: {voice_filename}")

        # 2. Очищаем голосовое аудио
        denoised_filename = f"denoised_{uuid.uuid4().hex}.wav"
        try:
            denoise_audio(voice_filename, denoised_filename)
        except Exception as e:
            logger.error(f"⚠️ Denoise failed: {e}")
            denoised_filename = voice_filename  # fallback

        # 3. Обрабатываем и миксуем с музыкой
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        try:
            logger.info("🎵 Mixing audio with music...")
            mix_voice_with_music(denoised_filename, output_filename, GITHUB_MUSIC_URL)
            logger.info("✅ Audio mixed successfully")
        except Exception as e:
            cleanup(voice_filename)
            cleanup(denoised_filename)
            return jsonify({"error": f"Audio processing failed: {str(e)}"}), 500

        # 4. Создаём ссылку для скачивания
        download_url = f"{request.host_url}download/{output_filename}"

        # 5. Очистка временных файлов
        cleanup(voice_filename)
        cleanup(denoised_filename)

        response_data = {
            "status": "success",
            "message": "Audio processed successfully",
            "download_url": download_url,
            "file_name": output_filename,
            "client_id": client_id,
            "name": name,
            "processed_at": time.time()
        }
        logger.info(f"✅ Success: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Error in /process_audio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(os.getcwd(), safe_filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True, download_name=f"voice_mix_{safe_filename}")

def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"🗑️ Deleted: {filename}")
    except Exception as e:
        logger.error(f"⚠️ Cleanup error for {filename}: {e}")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    logger.info("🌐 Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=False)
