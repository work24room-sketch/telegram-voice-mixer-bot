import os
import requests
import subprocess
import tempfile

def download_background_music(github_raw_url, local_filename):
    """Скачивает фоновую музыку из GitHub"""
    response = requests.get(github_raw_url)
    response.raise_for_status()
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    return local_filename

def get_audio_duration(file_path):
    """Получает длительность аудиофайла в миллисекундах"""
    cmd = [
        'ffprobe', 
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration_seconds = float(result.stdout.strip())
    return int(duration_seconds * 1000)  # Конвертируем в миллисекунды

def mix_voice_with_music(voice_file_path, output_path, github_music_url):
    """
    Основная функция обработки с использованием ffmpeg:
    1. Загружает голосовое сообщение
    2. Загружает фоновую музыку
    3. Подрезает музыку под длину голоса + паузы
    4. Добавляет fade in и fade out
    5. Миксует и экспортирует результат
    """

    # Параметры
    start_pause_ms = 1000  # Пауза в начале (1 секунда)
    end_pause_ms = 2000    # Пауза в конце (2 секунды)
    fade_duration_ms = 1500 # Длительность затухания (1.5 секунды)

    # Создаем временные файлы
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_music:
        bg_music_file = temp_music.name

    try:
        # Скачиваем фоновую музыку
        download_background_music(github_music_url, bg_music_file)
        
        # Получаем длительность голоса
        voice_duration = get_audio_duration(voice_file_path)
        
        # Рассчитываем необходимую длину музыки: голос + паузы
        required_music_length = voice_duration + start_pause_ms + end_pause_ms
        
        # Получаем длительность музыки
        music_duration = get_audio_duration(bg_music_file)
        
        # Создаем временный файл для обработанной музыки
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_processed_music:
            processed_music_file = temp_processed_music.name

        # Обрабатываем музыку: зацикливаем, обрезаем, добавляем fade
        if music_duration < required_music_length:
            # Зацикливаем музыку
            loop_count = (required_music_length // music_duration) + 2  # +2 для запаса
            cmd_loop = [
                'ffmpeg', '-y',
                '-stream_loop', str(loop_count),
                '-i', bg_music_file,
                '-c', 'copy',
                '-t', f'{required_music_length / 1000:.2f}',
                processed_music_file
            ]
            subprocess.run(cmd_loop, check=True)
        else:
            # Просто копируем и обрезаем
            cmd_trim = [
                'ffmpeg', '-y',
                '-i', bg_music_file,
                '-t', f'{required_music_length / 1000:.2f}',
                processed_music_file
            ]
            subprocess.run(cmd_trim, check=True)

        # Добавляем fade in и fade out к музыке
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_faded_music:
            faded_music_file = temp_faded_music.name

        cmd_fade = [
            'ffmpeg', '-y',
            '-i', processed_music_file,
            '-af', f'afade=t=in:st=0:d={fade_duration_ms/1000:.2f},'
                   f'afade=t=out:st={(required_music_length - fade_duration_ms)/1000:.2f}:d={fade_duration_ms/1000:.2f}',
            faded_music_file
        ]
        subprocess.run(cmd_fade, check=True)

        # Создаем паузу в начале
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_silence:
            silence_file = temp_silence.name

        cmd_silence = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'anullsrc=r=44100:cl=stereo:d={start_pause_ms/1000:.2f}',
            silence_file
        ]
        subprocess.run(cmd_silence, check=True)

        # Создаем финальную дорожку с паузами
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_final_track:
            final_track_file = temp_final_track.name

        # Объединяем паузу + голос + паузу в конце
        cmd_concat = [
            'ffmpeg', '-y',
            '-i', silence_file,
            '-i', voice_file_path,
            '-i', f'anullsrc=r=44100:cl=stereo:d={end_pause_ms/1000:.2f}',
            '-filter_complex', '[0:a][1:a][2:a]concat=n=3:v=0:a=1',
            final_track_file
        ]
        subprocess.run(cmd_concat, check=True)

        # Микшируем голос с музыкой
        cmd_mix = [
            'ffmpeg', '-y',
            '-i', final_track_file,
            '-i', faded_music_file,
            '-filter_complex', 
            f'[0:a]volume=1.0[voice];'
            f'[1:a]volume=0.3[music];'
            f'[voice][music]amix=inputs=2:duration=first:dropout_transition=2',
            output_path
        ]
        subprocess.run(cmd_mix, check=True)

    finally:
        # Очищаем временные файлы
        for temp_file in [bg_music_file, processed_music_file, faded_music_file, 
                         silence_file, final_track_file]:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

    return output_path
