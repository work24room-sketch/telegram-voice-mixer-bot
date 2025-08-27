import requests
import os
from pydub import AudioSegment

import sys
print(">>> Python version:", sys.version, flush=True)

def mix_voice_with_music(voice_path, output_path, music_url):
    """
    Накладывает голосовое сообщение на фоновую музыку.
    Убирает потрескивания: нормализуем sample rate, каналы, добавляем fade-in/out.
    """

    # === Загружаем голос ===
    voice = AudioSegment.from_file(voice_path, format="ogg")
    # Приводим к общему формату
    voice = voice.set_frame_rate(44100).set_channels(2)

    # Добавляем плавный fade-in/out (по 20 мс)
    voice = voice.fade_in(20).fade_out(20)

    # === Загружаем музыку ===
    music_filename = "background_music.mp3"
    if not os.path.exists(music_filename):
        r = requests.get(music_url, timeout=30)
        r.raise_for_status()
        with open(music_filename, "wb") as f:
            f.write(r.content)

    music = AudioSegment.from_file(music_filename, format="mp3")
    music = music.set_frame_rate(44100).set_channels(2)

    # === Выравниваем длину ===
    if len(music) < len(voice):
        # Зацикливаем музыку, если она короче голоса
        times = int(len(voice) / len(music)) + 1
        music = music * times
    else:
        music = music[:len(voice)]

    # === Смешиваем ===
    mixed = music.overlay(voice)

    # === Экспортируем с нормальным битрейтом ===
    mixed.export(output_path, format="mp3", bitrate="192k")
