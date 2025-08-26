@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.get_json()
        voice_url = data.get("voice_url")  # ← Прямая ссылка на файл
        client_id = data.get("client_id")
        
        print(f"🎯 Received voice_url: {voice_url}")
        
        if not voice_url or not voice_url.startswith('http'):
            return jsonify({
                "status": "error", 
                "message": "Invalid voice URL"
            }), 400

        # 1. Скачиваем голосовое сообщение по прямой ссылке
        print("📥 Downloading voice message...")
        voice_response = requests.get(voice_url)
        voice_response.raise_for_status()  # Проверяем ошибки

        # 2. Сохраняем временный файл
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)
        print(f"💾 Saved as: {voice_filename}")

        # 3. Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        print("🎵 Mixing audio with music...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # 4. Отправляем результат через Telegram API
        print("📤 Sending result to user...")
        with open(output_path, "rb") as audio_file:
            files = {'audio': audio_file}
            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
            send_data = {
                'client_id': client_id,
                'title': '🎵 Ваш микс!',
                'caption': 'Готовое аудио с фоновой музыкой'
            }
            send_response = requests.post(send_url, data=send_data, files=files)
            ready_file_id = send_response.json()['result']['audio']['file_id']

        # 5. Очистка
        cleanup(voice_filename)
        cleanup(output_path)

        return jsonify({
            "status": "success",
            "ready_file_id": ready_file_id,
            "message": "Audio processed successfully"
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
