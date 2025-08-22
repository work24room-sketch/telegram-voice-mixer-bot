import os
import requests
from pydub import AudioSegment
from pydub.utils import which

# Указываем путь к ffmpeg (важно для Render)
AudioSegment.converter = which("ffmpeg")

def download_background_music(github_raw_url, local_filename):
    """Скачивает фоновую музыку из GitHub"""
    response = requests.get(github_raw_url)
    response.raise_for_status()
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    return AudioSegment.from_file(local_filename, format="mp3")

def mix_voice_with_music(voice_file_path, output_path, github_music_url):
    """
    Основная функция обработки
    """

    # Параметры
    start_pause_ms = 1000
    end_pause_ms = 2000
    fade_duration_ms = 1500

    # Загружаем голосовое сообщение
    voice_audio = AudioSegment.from_file(voice_file_path)
    voice_duration = len(voice_audio)

    # Скачиваем и загружаем фоновую музыку
    bg_music_file = "background_music.mp3"
    bg_music = download_background_music(github_music_url, bg_music_file)

    # Рассчитываем необходимую длину музыки
    required_music_length = voice_duration + start_pause_ms + end_pause_ms

    # Если музыка короче, чем нужно, зацикливаем ее
    if len(bg_music) < required_music_length:
        num_loops = (required_music_length // len(bg_music)) + 1
        bg_music = bg_music * num_loops

    # Обрезаем музыку до нужной длины
    bg_music = bg_music[:required_music_length]

    # Применяем fade in и fade out
    bg_music = bg_music.fade_in(fade_duration_ms).fade_out(fade_duration_ms)

    # Создаем аудиодорожку с паузами
    final_track = AudioSegment.silent(duration=start_pause_ms)
    final_track = final_track.overlay(voice_audio, position=start_pause_ms)
    final_track = final_track + AudioSegment.silent(duration=end_pause_ms)

    # Накладываем музыку
    mixed = final_track.overlay(bg_music, gain_during_overlay=-10)

    # Экспортируем результат
    mixed.export(output_path, format="mp3")

    # Удаляем временный файл музыки
    if os.path.exists(bg_music_file):
        os.remove(bg_music_file)

    return output_path
