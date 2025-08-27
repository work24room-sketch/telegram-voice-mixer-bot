import os
import requests
from pydub import AudioSegment
from pydub.utils import which

# Указываем путь к ffmpeg (важно для Render)
AudioSegment.converter = which("ffmpeg")

def download_background_music(github_raw_url, local_filename):
    """Скачивает фоновую музыку из GitHub"""
    response = requests.get(github_raw_url)
    response.raise_for_status()  # Проверяем на ошибки
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    return AudioSegment.from_file(local_filename, format="mp3")

def mix_voice_with_music(voice_file_path, output_path, github_music_url):
    """
    Основная функция обработки:
    1. Загружает голосовое сообщение
    2. Загружает фоновую музыку
    3. Подрезает музыку под длину голоса + паузы
    4. Добавляет fade in и fade out
    5. Миксует и экспортирует результат
    """

    # Параметры (можно вынести в конфиг)
    start_pause_ms = 1000  # Пауза в начале (1 секунда)
    end_pause_ms = 2000    # Пауза в конце (2 секунды)
    fade_duration_ms = 1500 # Длительность затухания (1.5 секунды)

    # Загружаем голосовое сообщение
    voice_audio = AudioSegment.from_file(voice_file_path)
    voice_duration = len(voice_audio)

    # Скачиваем и загружаем фоновую музыку
    bg_music_file = "background_music.mp3"
    bg_music = download_background_music(github_music_url, bg_music_file)

    # Рассчитываем необходимую длину музыки: голос + паузы
    required_music_length = voice_duration + start_pause_ms + end_pause_ms

    # Если музыка короче, чем нужно, зацикливаем ее.
    # Если длиннее - обрезаем.
    if len(bg_music) < required_music_length:
        # Считаем, сколько раз нужно повторить трек
        num_loops = (required_music_length // len(bg_music)) + 1
        bg_music = bg_music * num_loops

    # Обрезаем музыку до нужной длины
    bg_music = bg_music[:required_music_length]

    # Применяем fade in к началу и fade out к концу музыки
    bg_music = bg_music.fade_in(fade_duration_ms).fade_out(fade_duration_ms)

    # Создаем аудиодорожку с паузами
    # 1. Пауза в начале
    final_track = AudioSegment.silent(duration=start_pause_ms)
    # 2. Добавляем голос поверх тишины (пауза уже есть)
    final_track = final_track.overlay(voice_audio, position=start_pause_ms)
    # 3. Добавляем паузу в конце (путем расширения дорожки)
    final_track = final_track + AudioSegment.silent(duration=end_pause_ms)

    # Накладываем подготовленную музыку на финальную дорожку (голос + паузы)
    # Уровень громкости музыки можно регулировать (например, -10 dB)
    mixed = final_track.overlay(bg_music, gain_during_overlay=-10)

    # Экспортируем результат
    mixed.export(output_path, format="mp3")

    # Удаляем временный файл музыки (опционально)
    if os.path.exists(bg_music_file):
        os.remove(bg_music_file)

    return output_path
