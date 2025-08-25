import os
import uuid
import time
import requests
from flask import Flask, request, jsonify, send_file
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Flask ---
app = Flask(__name__)

# ==================== ЭНДПОИНТЫ ====================

@app.route("/test", methods=["GET", "POST"])
def test_endpoint():
    print("✅ Тестовый запрос получен!")
    print("Headers:", dict(request.headers))
    print("Data:", request.get_json())
    return jsonify({"status": "test_ok", "message": "Request received"})

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
        voice_file_url = data.get("voice_file_url")
        chat_id = data.get("chat_id")
        attachments_json = data.get("attachments_json")
        
        if not voice_file_url:
            return jsonify({
                "status": "error", 
                "message": "Missing voice_file_url",
                "voice_file_url": "",
                "attachments_json": ""
            }), 400

        # 1. Скачиваем голосовое сообщение по URL
        voice_response = requests.get(voice_file_url)
        voice_response.raise_for_status()

        # 2. Сохраняем временный файл
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # 3. Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # 4. Отправляем готовый файл пользователю через Telegram API
        with open(output_path, "rb") as audio_file:
            files = {'audio': audio_file}
            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
            send_data = {
                'chat_id': chat_id,
                'title': '🎵 Ваш микс!',
                'caption': 'Готовое аудио с фоновой музыкой'
            }
            send_response = requests.post(send_url, data=send_data, files=files)
            send_response.raise_for_status()
            ready_file_id = send_response.json()['result']['audio']['file_id']

        # 5. Очистка временных файлов
        cleanup(voice_filename)
        cleanup(output_path)

        # 6. Возвращаем ответ для SaleBot
        return jsonify({
            "status": "success",
            "ready_file_id": ready_file_id,
            "message": "Audio processed successfully",
            "voice_file_url": voice_file_url,
            "attachments_json": attachments_json
        })

    except Exception as e:
        print("❌ Error:", str(e))
        # Очистка в случае ошибки
        if 'voice_filename' in locals() and os.path.exists(voice_filename):
            cleanup(voice_filename)
        if 'output_path' in locals() and os.path.exists(output_path):
            cleanup(output_path)
            
        return jsonify({
            "status": "error", 
            "message": f"Ошибка обработки: {str(e)}",
            "voice_file_url": "",
            "attachments_json": ""
        }), 500

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
            print(f"✅ Удален файл: {filename}")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении файла {filename}: {e}")

# ==================== ЗАПУСК СЕРВЕРА ====================
if __name__ == "__main__":
    print("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
