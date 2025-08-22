from flask import Flask, request, jsonify, send_file
import os
import uuid
from audio_processor import mix_voice_with_music

app = Flask(__name__)

# Конфигурация (лучше вынести в переменные окружения)
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3" # ЗАМЕНИТЕ НА СВОЙ URL!

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        data = request.get_json()
        voice_file_path = data.get('voice_file_path')

        if not voice_file_path or not os.path.exists(voice_file_path):
            return jsonify({"error": "File not found"}), 400

        # Генерируем уникальное имя для выходного файла
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        # Обрабатываем аудио
        result_path = mix_voice_with_music(voice_file_path, output_path, GITHUB_MUSIC_URL)

        # Возвращаем имя обработанного файла
        return jsonify({"processed_file": output_filename})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint для скачивания готового файла"""
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)