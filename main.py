@app.route("/process_audio", methods=["POST"])
def process_audio():
    """Основной эндпоинт для обработки аудио"""
    try:
        # Логируем заголовки для диагностики
        print(f"📋 Content-Type: {request.content_type}")

        # Пробуем получить данные разными способами
        data = None
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            data = request.get_json(force=True, silent=True)

        if data is None:
            data = request.form.to_dict()

        print(f"📦 Received data: {data}")

        # --- Извлечение параметров ---
        voice_file_url = data.get("voice_file_url")
        chat_id = data.get("chat_id")
        attachments_json = data.get("attachments_json")

        # --- ДЕТАЛЬНАЯ ПРОВЕРКА ДАННЫХ ---
        if not voice_file_url or voice_file_url == "None":
            print(f"❌ Invalid voice_file_url: {voice_file_url}")
            return jsonify({
                "status": "error",
                "message": "Missing or invalid voice_file_url",
                "voice_file_url": str(voice_file_url),
                "attachments_json": str(attachments_json)
            }), 400

        if not voice_file_url.startswith(('http://', 'https://')):
            print(f"❌ Invalid URL scheme: {voice_file_url}")
            return jsonify({
                "status": "error",
                "message": f"Invalid URL scheme: {voice_file_url}",
                "voice_file_url": voice_file_url,
                "attachments_json": attachments_json
            }), 400

        # --- Скачиваем голосовое сообщение ---
        print(f"📥 Downloading from: {voice_file_url}")
        voice_response = requests.get(voice_file_url)
        voice_response.raise_for_status()

        # --- Сохраняем временный файл ---
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        # --- Обрабатываем аудио ---
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # --- Отправляем готовый файл пользователю через Telegram API ---
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

        # --- Очистка временных файлов ---
        cleanup(voice_filename)
        cleanup(output_path)

        # --- Ответ для SaleBot ---
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
