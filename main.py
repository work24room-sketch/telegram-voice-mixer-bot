# Добавьте этот импорт в начало файла
import logging
from logging.handlers import RotatingFileHandler
import sys

# --- Настройка логирования ---
def setup_logging():
    # Создаем логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler (для Render)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (для файла логов)
    file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logging.info("✅ Логирование настроено")

# --- Конфигурация ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GITHUB_MUSIC_URL = "https://raw.githubusercontent.com/work24room-sketch/telegram-voice-mixer-bot/main/background_music.mp3"

# --- Инициализация Telegram бота ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Обработчики Telegram ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logging.info(f"Команда /start от пользователя {message.from_user.id}")
    bot.reply_to(message, "🎵 Привет! Отправь мне голосовое сообщение, и я добавлю к нему фоновую музыку!")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    logging.info(f"Голосовое сообщение от пользователя {message.from_user.id}")
    bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем информацию о файле для передачи в Salebot
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"
        
        logging.info(f"Файл голосового сообщения: {file_url}")
        
        # Формируем сообщение о перенаправлении
        redirect_text = (
            "🎵 Спасибо за голосовое сообщение! \n\n"
            "Для обработки и микширования с музыкой, пожалуйста, "
            "воспользуйтесь нашим основным чат-ботом. \n\n"
            "Перейдите в @YourSaleBotName для продолжения работы 😊"
        )
        
        bot.reply_to(message, redirect_text)
        logging.info(f"Перенаправление отправлено пользователю {message.from_user.id}")
        
    except Exception as e:
        error_msg = f"Ошибка перенаправления: {e}"
        logging.error(error_msg)
        bot.reply_to(message, "❌ Произошла ошибка при обработке запроса")
    
    return

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    logging.info(f"Текстовое сообщение от пользователя {message.from_user.id}: {message.text}")
    bot.reply_to(message, "Отправьте мне голосовое сообщение 🎤")

# --- Функция очистки ---
def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logging.info(f"Файл удален: {filename}")
    except Exception as e:
        logging.error(f"Ошибка при удалении файла {filename}: {e}")

# --- Инициализация Flask ---
app = Flask(__name__)

# --- Эндпоинты Flask ---
@app.route("/health")
def health_check():
    logging.info("Health check request")
    return jsonify({"status": "healthy", "service": "voice-mixer-api", "timestamp": time.time(), "version": "1.0"})

@app.route("/")
def index():
    logging.info("Root request")
    return "🎵 Voice Mixer Bot is running! Use /health for status check."

@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        logging.info("Process audio request")
        # Ваш код для обработки аудио через API
        return jsonify({"status": "success", "message": "Audio processing endpoint"})
    except Exception as e:
        logging.error(f"Error in process_audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        logging.info(f"Download request for file: {filename}")
        # Ваш код для скачивания файлов
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading file {filename}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404

@app.route("/api/generate", methods=["POST"])
def generate_for_salebot():
    try:
        logging.info("API generate request from Salebot")
        data = request.get_json()
        
        if not data or 'voice_message_url' not in data:
            logging.warning("Missing voice_message_url in request")
            return jsonify({
                "status": "error",
                "message": "Missing required field: voice_message_url"
            }), 400
        
        client_id = data.get('client_id', 'unknown')
        name = data.get('name', 'Guest')
        voice_url = data['voice_message_url']
        
        logging.info(f"Processing audio for client: {client_id}, name: {name}")
        
        # Скачиваем голосовое сообщение
        voice_filename = f"voice_{uuid.uuid4().hex}.ogg"
        
        response = requests.get(voice_url)
        if response.status_code != 200:
            logging.error(f"Failed to download voice message: {response.status_code}")
            return jsonify({
                "status": "error",
                "message": f"Failed to download voice message: {response.status_code}"
            }), 400
        
        with open(voice_filename, "wb") as f:
            f.write(response.content)
        
        logging.info(f"Voice message downloaded: {voice_filename}")
        
        # Обрабатываем аудио
        output_filename = f"mixed_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        logging.info("Starting audio processing...")
        mix_voice_with_music(voice_filename, output_path, GITHUB_MUSIC_URL)
        logging.info("Audio processing completed")
        
        # Формируем URL для скачивания
        download_url = urljoin(request.host_url, f"download/{output_filename}")
        
        # Очистка временных файлов
        cleanup(voice_filename)
        
        logging.info(f"Audio ready for download: {download_url}")
        
        return jsonify({
            "status": "success",
            "message": "Audio mixed successfully",
            "download_url": download_url,
            "filename": output_filename
        })
        
    except Exception as e:
        error_msg = f"Error processing audio: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 500

# --- Инициализация приложения ---
def create_app():
    # Настраиваем логирование при инициализации
    setup_logging()
    logging.info("🚀 Приложение инициализировано!")
    return app

# --- Точка входа для Gunicorn ---
application = create_app()

if __name__ == "__main__":
    # Настраиваем логирование
    setup_logging()
    logging.info("🌐 Запускаем Flask-сервер...")
    app.run(host="0.0.0.0", port=5000, debug=False)
