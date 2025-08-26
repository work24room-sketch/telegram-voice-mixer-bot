import requests
import json

def handler(event, context):
    # Логируем всё, что приходит
    print("EVENT:", json.dumps(event, ensure_ascii=False))

    # Инициализируем переменные
    file_url = None

    # 1. Если это attachment (файл, картинка и т.д.)
    if "attachment" in event:
        attachment = event.get("attachment", {})
        if "payload" in attachment and "url" in attachment["payload"]:
            file_url = attachment["payload"]["url"]

    # 2. Если это текст, пробуем достать ссылку
    elif "message" in event:
        text = event.get("message", "")
        if "http" in text:
            file_url = text

    # Если ссылки нет – отвечаем пользователю
    if not file_url:
        return {
            "text": "Отправь, пожалуйста, файл или ссылку 📎"
        }

    # Отправляем на твой тестовый сервер (замени URL на свой)
    webhook_url = "https://your-render-test-service.onrender.com/webhook"
    payload = {"file_url": file_url}

    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        print("WEBHOOK STATUS:", r.status_code, r.text)
    except Exception as e:
        print("WEBHOOK ERROR:", e)

    # Ответ пользователю
    return {
        "text": f"✅ Ссылка получена и отправлена: {file_url}"
    }
