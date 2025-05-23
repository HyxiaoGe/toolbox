import subprocess
from datetime import timedelta
from pathlib import Path
import os

def get_video_duration(file_path, ffprobe_path):
    if not os.path.isfile(ffprobe_path):
        raise FileNotFoundError(f"ffprobe.exe not found at the specified path: {ffprobe_path}")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")

    try:
        result = subprocess.run(
            [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.stderr:
            raise Exception(f"ffprobe error for {os.path.basename(file_path)}: {result.stderr.strip()}")
        duration = float(result.stdout.strip())
        return duration
    except ValueError as e:
        raise ValueError(f"Could not convert duration to float for {os.path.basename(file_path)}: {result.stdout.strip()} ({e})")
    except Exception as e_run:
        raise Exception(f"Error running ffprobe for {os.path.basename(file_path)}: {e_run}")

def format_duration_to_hhmmss(seconds):
    if seconds < 0:
        seconds = 0
    return str(timedelta(seconds=seconds)).split(".")[0]

def sum_mp4_durations_in_directory(directory_path, ffprobe_path):
    """
    计算目录及其子目录中所有 .mp4 文件的总时长。
    返回: (总时长_秒, 已处理文件数, 日志消息列表, 错误列表)
    """
    total_duration = 0.0
    processed_files_count = 0
    log_messages = []
    error_list = []

    if not os.path.isdir(directory_path):
        log_messages.append(f"Error: Directory '{directory_path}' not found.")
        return total_duration, processed_files_count, log_messages, error_list
    
    log_messages.append(f"Starting duration scan in '{directory_path}' using ffprobe at '{ffprobe_path}'.")

    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.mp4'):
                file_full_path = Path(root) / file
                try:
                    duration = get_video_duration(file_full_path, ffprobe_path)
                    formatted_individual_duration = format_duration_to_hhmmss(duration)
                    log_messages.append(f"  Processed '{file_full_path.name}': {formatted_individual_duration} ({duration:.2f}s)")
                    total_duration += duration
                    processed_files_count += 1
                except Exception as e:
                    err_msg = f"  Error processing '{file_full_path.name}': {e}"
                    log_messages.append(err_msg)
                    error_list.append(err_msg)
    
    formatted_total = format_duration_to_hhmmss(total_duration)
    summary_msg = f"Scan complete. Processed {processed_files_count} MP4 files. Total duration: {formatted_total}. Errors: {len(error_list)}."
    log_messages.append(summary_msg)
    return total_duration, processed_files_count, log_messages, error_list
