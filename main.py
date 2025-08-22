import threading
from flask import Flask, request, jsonify, send_file
import telebot
import os
import requests
import uuid
from audio_processor import mix_voice_with_music

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"  # ЗАМЕНИТЕ!

# --- Инициализация Flask ---
app = Flask(__name__)

# --- Эндпоинты Flask ---
@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        data = request.get_json()
        voice_file_path = data.get('voice_file_path')

        if not voice_file_path or not os.path.exists(voice_file_path):
            return jsonify({"error": "File not found"}), 400

        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)

        result_path = mix_voice_with_music(voice_file_path, output_path, GITHUB_MUSIC_URL)
        return jsonify({"processed_file": output_filename})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Инициализация Telegram бота ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        bot.send_chat_action(message.chat.id, 'upload_audio')
        
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Отправляем файл на обработку (теперь на этот же сервер!)
        process_url = "http://localhost:5000/process_audio"
        payload = {"voice_file_path": voice_filename}
        response = requests.post(process_url, json=payload)
        response.raise_for_status()
        result_data = response.json()
        result_filename = result_data['processed_file']

        # Скачиваем готовый файл
        download_url = f"http://localhost:5000/download/{result_filename}"
        mixed_audio_response = requests.get(download_url)
        mixed_audio_response.raise_for_status()

        with open(result_filename, 'wb') as f:
            f.write(mixed_audio_response.content)

        # Отправляем пользователю
        with open(result_filename, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file, title="Ваш микс!")

        # Удаляем временные файлы
        cleanup(voice_filename)
        cleanup(result_filename)

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")

def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except:
        pass

# --- Запуск в отдельном потоке ---
def run_bot():
    print("Запускаем Telegram-бота...")
    bot.polling(none_stop=True)

# --- Главная функция ---
if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем Flask-сервер
    print("Запускаем Flask-сервер...")
    app.run(host='0.0.0.0', port=5000, debug=False)
