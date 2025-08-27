import os
import uuid
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_file
import requests
from urllib.parse import urljoin
from pydub import AudioSegment  # убедись, что pydub установлена

# --- Настройка логирования ---
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.info("✅ Логирование настроено")

# --- Конфигурация ---
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Flask ---
app = Flask(__name__)
setup_logging()

# --- Вспомогательные функции ---
def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logging.info(f"Файл удален: {filename}")
    except Exception as e:
        logging.error(f"Ошибка при удалении файла {filename}: {e}")

def mix_voice_with_music(voice_path, output_path, music_url):
    """
    Скачивает музыку, микширует с голосовым сообщением и сохраняет mp3
    """
    try:
        logging.info("Скачиваем фоновую музыку...")
        r = requests.get(music_url)
        music_file = f"music_{uuid.uuid4().hex}.mp3"
        with open(music_file, "wb") as f:
            f.write(r.content)

        logging.info("Загружаем аудио...")
        voice = AudioSegment.from_file(voice_path)
        music = AudioSegment.from_file(music_file)

        # Длительность музыки = длительность голосового
        if len(music) < len(voice):
            # повторяем музыку
            times = len(voice) // len(music) + 1
            music = music * times
        music = music[:len(voice)]

        logging.info("Микшируем аудио...")
        mixed = voice.overlay(music)
        mixed.export(output_path, format="mp3")
        logging.info(f"Аудио сохранено: {output_path}")

        # удаляем временную музыку
        cleanup(music_file)
    except Exception as e:
        logging.error(f"Ошибка микширования: {e}")
        raise

# --- Эндпоинты ---
@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "voice-mixer-api",
        "timestamp": time.time(),
        "version": "1.0"
    })

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading file {filename}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404

@app.route("/api/generate", methods=["POST"])
def generate_for_salebot():
    try:
        logging.info("API generate request from Salebot")
        data = request.get_json()

        if not data or 'voice_message_url' not in data:
            logging.warning("Missing voice_message_url in request")
            return jsonify({
                "status": "error",
                "message": "Missing required field: voice_message_url"
            }), 400

        voice_url = data['voice_message_url']
        client_id = data.get('client_id', 'unknown')
        name = data.get('name', 'Guest')

        logging.info(f"Processing audio for client: {client_id}, name: {name}")

        # скачиваем голосовое
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        response = requests.get(voice_url)
        if response.status_code != 200:
            logging.error(f"Failed to download voice message: {response.status_code}")
            return jsonify({
                "status": "error",
                "message": f"Failed to download voice message: {response.status_code}"
            }), 400

        with open(voice_filename, "wb") as f:
            f.write(response.content)
        logging.info(f"Voice message downloaded: {voice_filename}")

        # микшируем
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # формируем ссылку на скачивание
        download_url = urljoin(request.host_url, f"download/{output_filename}")

        # удаляем временные файлы
        cleanup(voice_filename)

        logging.info(f"Audio ready for download: {download_url}")
        return jsonify({
            "status": "success",
            "download_url": download_url,
            "filename": output_filename
        })

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Точка входа ---
if __name__ == "__main__":
    logging.info("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
