import os
import requests
import subprocess
import tempfile

def mix_voice_with_music(voice_file_path, output_path, github_music_url):
    """
    Альтернативная реализация без pydub
    Используем ffmpeg напрямую через командную строку
    """
    
    # Параметры
    start_pause = 1.0  # Пауза в начале (1 секунда)
    end_pause = 2.0    # Пауза в конце (2 секунды)
    fade_duration = 1.5  # Длительность затухания (1.5 секунды)
    music_volume = 0.3  # Уровень громкости музыки (30%)

    # Скачиваем фоновую музыку
    response = requests.get(github_music_url)
    response.raise_for_status()
    
    # Создаем временные файлы
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as music_file:
        music_file.write(response.content)
        music_path = music_file.name

    try:
        # Получаем длительность голосового сообщения
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
            voice_file_path
        ], capture_output=True, text=True)
        
        voice_duration = float(result.stdout.strip())
        
        # Рассчитываем общую длительность
        total_duration = voice_duration + start_pause + end_pause

        # Команда ffmpeg для создания микса
        command = [
            'ffmpeg',
            '-y',  # overwrite output file
            # Добавляем паузу в начале
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo:d={start_pause}',
            # Добавляем голосовое сообщение
            '-i', voice_file_path,
            # Добавляем музыку (зацикленную)
            '-i', music_path,
            # Фильтры:
            '-filter_complex', 
            f'[2:a]volume={music_volume},aloop=loop=-1:size=2e+09[bg];'  # Уменьшаем громкость музыки и зацикливаем
            f'[bg]atrim=0:{total_duration},afade=t=in:st=0:d={fade_duration},afade=t=out:st={total_duration - fade_duration}:d={fade_duration}[music];'  # Обрезаем музыку и добавляем fade
            f'[0:a][1:a]concat=n=2:v=0:a=1[voice_with_pause];'  # Объединяем паузу и голос
            f'[voice_with_pause]apad=pad_dur={end_pause}[voice_final];'  # Добавляем паузу в конце
            f'[voice_final][music]amix=inputs=2:duration=longest[final]',  # Микшируем голос и музыку
            '-map', '[final]',
            '-ac', '2',
            '-ar', '44100',
            output_path
        ]

        # Выполняем команду
        subprocess.run(command, check=True, capture_output=True)
        
        return output_path

    finally:
        # Удаляем временный файл музыки
        if os.path.exists(music_path):
            os.remove(music_path)
