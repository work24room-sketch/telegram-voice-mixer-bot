import os
import uuid
import time
from flask import Flask, request, jsonify, send_file
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
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
        voice_file_path = data.get("voice_file_path")  # Локальный путь или URL .ogg

        if not voice_file_path:
            return jsonify({"status": "error", "message": "Missing voice_file_path"}), 400

        # Создаем уникальное имя файла для микса
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        # Обработка аудио
        mix_voice_with_music(voice_file_path, output_path, GITHUB_MUSIC_URL)

        # Возвращаем имя файла (Salebot потом сможет скачать)
        return jsonify({
            "status": "success",
            "processed_file": output_filename
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Скачивание готового файла"""
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found"}), 404

def cleanup(filename):
    """Удаление временных файлов после обработки"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"⚠️ Ошибка при удалении файла {filename}: {e}")

# ==================== ЗАПУСК СЕРВЕРА ====================
if __name__ == "__main__":
    print("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
