import os
import requests
import subprocess
import tempfile

def mix_voice_with_music(voice_file_path, output_path, github_music_url):
    """
    Микширование голосового и фоновой музыки через ffmpeg (без pydub)
    """

    # Параметры
    start_pause = 1.0     # пауза в начале (сек)
    end_pause = 2.0       # пауза в конце (сек)
    fade_duration = 1.5   # затухание музыки (сек)
    music_volume = 0.3    # громкость музыки (30%)

    # Скачиваем фоновую музыку
    response = requests.get(github_music_url)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as music_file:
        music_file.write(response.content)
        music_path = music_file.name

    try:
        # Получаем длительность голосового
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            voice_file_path
        ], capture_output=True, text=True, check=True)

        voice_duration = float(result.stdout.strip())
        total_duration = voice_duration + start_pause + end_pause

        # Формируем команду ffmpeg
        command = [
            "ffmpeg",
            "-y",
            "-i", voice_file_path,
            "-i", music_path,
            "-filter_complex",
            # 0:a → voice, 1:a → music
            f"[0:a]adelay={int(start_pause*1000)}|{int(start_pause*1000)},"
            f"apad=pad_dur={end_pause},"
            f"aformat=channel_layouts=stereo:sample_rates=44100[voice];"
            f"[1:a]volume={music_volume},aloop=loop=-1:size=2e+09,"
            f"atrim=0:{total_duration},"
            f"afade=t=in:st=0:d={fade_duration},"
            f"afade=t=out:st={total_duration-fade_duration}:d={fade_duration},"
            f"aformat=channel_layouts=stereo:sample_rates=44100[music];"
            f"[voice][music]amix=inputs=2:duration=longest[final]",
            "-map", "[final]",
            "-ac", "2",
            "-ar", "44100",
            output_path
        ]

        subprocess.run(command, check=True)

        return output_path

    finally:
        if os.path.exists(music_path):
            os.remove(music_path)
