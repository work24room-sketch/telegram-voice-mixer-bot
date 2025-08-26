from flask import Flask, request, jsonify
import os, uuid, requests
from audio_processor import mix_voice_with_music

app = Flask(__name__)

GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.get_json()
        print("📦 Received data:", data)

        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        # Скачиваем голосовое сообщение
        voice_response = requests.get(voice_url)
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # Подготавливаем имя файла для микса
        output_filename = f"mix_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        # Вызов функции микширования
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # Формируем публичный URL для SaleBot
        # Для Render можно просто host + filename, если файлы доступны
        mix_url = request.host_url + output_filename

        # Очистка временного голосового файла
        if os.path.exists(voice_filename):
            os.remove(voice_filename)

        return jsonify({
            "mix_result": mix_url,
            "client_id": client_id,
            "name": name
        })

    except Exception as e:
        print("❌ Ошибка:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
