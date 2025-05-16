import subprocess
from datetime import timedelta
from pathlib import Path
import os # Added for os.walk and path operations

DEFAULT_FFPROBE_PATH = r'D:\ffmpeg-7.0-full_build\bin\ffprobe.exe' # Keep a default for __main__

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
    Calculates the total duration of all .mp4 files in a directory and its subdirectories.
    Returns: (total_duration_seconds, processed_files_count, log_messages_list, error_list)
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


if __name__ == '__main__':
    # Example usage for standalone testing
    test_directory = r'E:\BaiduNetdiskDownload' # Replace with your test directory
    # For testing, you can override ffprobe_path if DEFAULT_FFPROBE_PATH is not correct
    # ffprobe_executable_path = input(f"Enter ffprobe.exe path or press Enter for default ({DEFAULT_FFPROBE_PATH}): ")
    # if not ffprobe_executable_path:
    #     ffprobe_executable_path = DEFAULT_FFPROBE_PATH
    ffprobe_executable_path = DEFAULT_FFPROBE_PATH # Using default for automated run

    print(f"Calculating total MP4 duration in: {test_directory}")
    print(f"Using ffprobe: {ffprobe_executable_path}")

    try:
        total_sec, num_files, logs, errors = sum_mp4_durations_in_directory(test_directory, ffprobe_executable_path)
        print("\n--- Logs ---")
        for log_entry in logs:
            print(log_entry)
        
        print("\n--- Summary ---")
        if errors:
            print(f"Completed with {len(errors)} errors.")
        print(f"Total files processed: {num_files}")
        print(f"Total duration: {format_duration_to_hhmmss(total_sec)} ({total_sec:.2f} seconds)")

    except FileNotFoundError as fnf_error:
        print(f"Error: {fnf_error}") 
    except Exception as e_main:
        print(f"An unexpected error occurred: {e_main}")
