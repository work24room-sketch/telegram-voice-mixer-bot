from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        data = request.json
        print("📋 Content-Type:", request.content_type)
        print("📦 Received data:", data)

        api_key = data.get("apiKey")
        voice_url = data.get("voice_url")
        client_id = data.get("client_id")  # уникальный ID клиента из SaleBot
        name = data.get("name")            # имя клиента

        if not voice_url:
            return jsonify({"error": "voice_url is required"}), 400

        # тут твоя логика обработки файла, например:
        mix_result = f"Обработан файл: {voice_url}, клиент: {client_id}, имя: {name}"

        return jsonify({
            "status": "ok",
            "client_id": client_id,
            "name": name,
            "mix_result": mix_result
        }), 200

    except Exception as e:
        print("❌ Ошибка:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
