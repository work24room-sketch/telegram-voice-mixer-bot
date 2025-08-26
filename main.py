from flask import Flask, request, jsonify
import requests, uuid, os
from pydub import AudioSegment

app = Flask(__name__)

# Фоновая музыка
BACKGROUND_MUSIC_PATH = "background.mp3"

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.json
        print("📦 Received data:", data)

        voice_url = data.get("voice_url")
        client_id = data.get("client_id")
        name = data.get("name")

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        # 1. Скачиваем голосовое сообщение
        voice_response = requests.get(voice_url)
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # 2. Конвертируем голос в AudioSegment
        voice_audio = AudioSegment.from_file(voice_filename)

        # 3. Загружаем фон
        background_audio = AudioSegment.from_file(BACKGROUND_MUSIC_PATH)

        # 4. Накладываем голос на фон
        mixed_audio = background_audio.overlay(voice_audio)

        # 5. Сохраняем микс
        output_filename = f"mix_{uuid.uuid4().hex}.mp3"
        mixed_audio.export(output_filename, format="mp3")

        # 6. Формируем URL для SaleBot
        mix_url = request.host_url + output_filename

        # 7. Чистим временные файлы
        os.remove(voice_filename)

        # 8. Возвращаем результат
        return jsonify({"mix_result": mix_url, "client_id": client_id, "name": name})

    except Exception as e:
        print("❌ Ошибка:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
