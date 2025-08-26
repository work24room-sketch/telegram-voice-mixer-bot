@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.get_json()
        voice_file_id = data.get("voice_file_id")
        chat_id = data.get("chat_id")
        
        if not voice_file_id or not chat_id:
            return jsonify({"status": "error", "message": "Missing parameters"}), 400

        # 1. Скачиваем голосовое сообщение
        file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={voice_file_id}"
        file_response = requests.get(file_info_url)
        file_path = file_response.json()['result']['file_path']
        
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        voice_response = requests.get(download_url)
        
        # 2. Обрабатываем аудио
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        with open(voice_filename, "wb") as f:
            f.write(voice_response.content)

        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)

        # 3. ВОЗВРАЩАЕМ ФАЙЛ (а не file_id)
        with open(output_path, "rb") as f:
            file_content = f.read()

        # 4. Очистка
        cleanup(voice_filename)
        cleanup(output_path)

        # 5. Возвращаем файл в base64 для SaleBot
        return jsonify({
            "status": "success",
            "message": "Audio processed successfully",
            "file_content": base64.b64encode(file_content).decode('utf-8'),
            "file_name": output_filename
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
