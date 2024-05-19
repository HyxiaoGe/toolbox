import subprocess
from datetime import timedelta
from pathlib import Path


def get_video_duration(file_path):
    # 调用 ffprobe 获取视频时长，输出为简洁文本格式
    ffprobe_path = r'D:\ffmpeg-7.0-full_build\bin\ffprobe.exe'
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 检查是否有错误输出
    if result.stderr:
        raise Exception("ffprobe error: " + result.stderr)

    # 解析输出中的时长信息
    try:
        duration = float(result.stdout.strip())
        return duration
    except ValueError as e:
        raise ValueError("Could not convert duration to float: " + str(e))


def sum_durations_in_directory(directory_path):
    total_duration = 0
    path = Path(directory_path)
    for file in path.glob('*.mp4'):
        duration = get_video_duration(file)
        total_duration += duration
        print(f"Processed {file}: {duration} seconds")
    return total_duration


def format_duration(duration):
    # 将秒数转换为时分秒格式(去除毫秒)
    return str(timedelta(seconds=duration)).split(".")[0]


if __name__ == '__main__':
    directory_path = 'E:\\test'
    try:
        duration = sum_durations_in_directory(directory_path)
        duration = format_duration(duration)
        print(f"Duration of {directory_path} is {duration} seconds")
    except Exception as e:
        print(f"An error occurred: {e}")
