from flask import Flask, request, jsonify, send_file
import os
import uuid
import time
import requests
import logging
import tempfile
from audio_processor import mix_voice_with_music

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# ==================== ФУНКЦИЯ ШУМОПОДАВЛЕНИЯ ====================

def apply_noise_reduction(input_audio_path, output_audio_path):
    """
    Применяет шумоподавление к аудиофайлу
    Возвращает True если успешно, False если нет
    """
    try:
        # Проверяем доступность библиотек для шумоподавления
        try:
            import noisereduce as nr
            import soundfile as sf
            from scipy.io import wavfile
        except ImportError:
            logger.warning("⚠️ Библиотеки шумоподавления не установлены. Пропускаем этап.")
            return False

        logger.info(f"🔇 Applying noise reduction to: {input_audio_path}")
        
        # Читаем аудиофайл
        if input_audio_path.endswith('.ogg'):
            # Конвертируем ogg в wav для обработки
            import subprocess
            wav_temp_path = f"temp_{uuid.uuid4().hex}.wav"
            
            # Конвертация ogg to wav using ffmpeg
            subprocess.run([
                'ffmpeg', '-i', input_audio_path, '-ar', '16000', 
                '-ac', '1', '-y', wav_temp_path
            ], check=True, capture_output=True)
            
            rate, data = wavfile.read(wav_temp_path)
            os.remove(wav_temp_path)  # удаляем временный wav
        else:
            rate, data = wavfile.read(input_audio_path)

        # Применяем шумоподавление
        reduced_noise = nr.reduce_noise(
            y=data, 
            sr=rate,
            prop_decrease=0.8,  # сила шумоподавления (80%)
            stationary=True
        )

        # Сохраняем результат
        wavfile.write(output_audio_path, rate, reduced_noise)
        logger.info(f"✅ Noise reduction applied: {output_audio_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Noise reduction failed: {str(e)}")
        return False

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
    """Основной эндпоинт для обработки аудио со шумоподавлением"""
    logger.info("🎯 /process_audio endpoint called!")
    
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ No data received")
            return jsonify({"error": "No data received"}), 400

        # Извлекаем параметры из SaleBot переменных
        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        logger.info(f"🔍 voice_url: {voice_url}")
        logger.info(f"🔍 client_id: {client_id}")
        logger.info(f"🔍 name: {name}")

        if not voice_url or voice_url == 'None':
            logger.error("❌ voice_url is required")
            return jsonify({"error": "voice_url is required"}), 400

        # 1. Скачиваем голосовое сообщение
        logger.info(f"📥 Downloading from: {voice_url}")
        try:
            voice_response = requests.get(voice_url, timeout=30)
            voice_response.raise_for_status()
        except Exception as e:
            logger.error(f"❌ Failed to download voice: {str(e)}")
            return jsonify({"error": f"Failed to download voice: {str(e)}"}), 400

        # 2. Сохраняем временный файл
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)
        logger.info(f"💾 Saved voice as: {voice_filename}")

        # 3. ШУМОПОДАВЛЕНИЕ (новый этап)
        cleaned_voice_filename = None
        try:
            cleaned_voice_filename = f"cleaned_voice_{uuid.uuid4().hex}.wav"
            noise_reduction_success = apply_noise_reduction(voice_filename, cleaned_voice_filename)
            
            if noise_reduction_success:
                logger.info("✅ Noise reduction successful")
                # Используем очищенный файл для микширования
                voice_for_mixing = cleaned_voice_filename
            else:
                logger.info("⚠️ Using original voice without noise reduction")
                voice_for_mixing = voice_filename
                
        except Exception as e:
            logger.error(f"⚠️ Noise reduction skipped: {str(e)}")
            voice_for_mixing = voice_filename

        # 4. Обрабатываем аудио (микширование с музыкой)
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        logger.info("🎵 Mixing audio with music...")
        try:
            mix_voice_with_music(voice_for_mixing, output_path, GITHUB_MUSIC_URL)
            logger.info("✅ Audio mixed successfully")
        except Exception as e:
            logger.error(f"❌ Audio processing failed: {str(e)}")
            # Очищаем все временные файлы при ошибке
            cleanup(voice_filename)
            if cleaned_voice_filename and os.path.exists(cleaned_voice_filename):
                cleanup(cleaned_voice_filename)
            return jsonify({"error": f"Audio processing failed: {str(e)}"}), 500

        # 5. Создаем URL для скачивания
        download_url = f"{request.host_url}download/{output_filename}"
        logger.info(f"🔗 Download URL: {download_url}")

        # 6. Очистка временных файлов (голосовых, но не финального микса)
        cleanup(voice_filename)
        if cleaned_voice_filename and os.path.exists(cleaned_voice_filename):
            cleanup(cleaned_voice_filename)

        # 7. Возвращаем ответ для SaleBot
        response_data = {
            "status": "success",
            "message": "Audio processed successfully with noise reduction",
            "download_url": download_url,
            "file_name": output_filename,
            "client_id": client_id,
            "name": name,
            "processed_at": time.time(),
            "noise_reduction_applied": noise_reduction_success if 'noise_reduction_success' in locals() else False
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
    try:
        # Проверяем безопасность пути
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(os.getcwd(), safe_filename)
        
        if not os.path.exists(file_path) or '..' in filename or '/' in filename:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"voice_mix_{safe_filename}"
        )
    
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 404

def cleanup(filename):
    """Удаление временных файлов после обработки"""
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
