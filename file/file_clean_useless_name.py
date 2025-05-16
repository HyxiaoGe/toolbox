import os
import re

# Patterns are defined globally or passed as an argument if they need to be configurable by GUI later
PATTERNS_TO_CLEAN = [
    r'www.zxit8.com_',
    r' - Copy',
    r'\s+(?=\.\w+$)',  # remove spaces before extension
    r'\d{2}_\d{2}_ev',
    r' \d{4}-\d{2}-\d{2}'
]

def clean_directory_filenames(directory_path, patterns=None):
    """
    Cleans filenames in the given directory and its subdirectories based on regex patterns.
    Returns a list of log messages and the count of renamed files.
    """
    if patterns is None:
        patterns = PATTERNS_TO_CLEAN
    
    log_messages = []
    renamed_count = 0
    processed_count = 0
    errors = []

    if not os.path.isdir(directory_path):
        log_messages.append(f"Error: Directory '{directory_path}' not found.")
        return log_messages, renamed_count, processed_count, errors

    for root, _, files in os.walk(directory_path):
        for filename in files:
            processed_count += 1
            original_filename = filename
            current_filename_state = filename

            for pattern in patterns:
                current_filename_state = re.sub(pattern, '', current_filename_state)
            
            current_filename_state = current_filename_state.strip() # Remove leading/trailing whitespace

            if current_filename_state != original_filename and current_filename_state: # ensure not empty
                original_path = os.path.join(root, original_filename)
                new_path = os.path.join(root, current_filename_state)
                try:
                    if os.path.exists(new_path) and original_path.lower() != new_path.lower():
                        log_msg = f'SKIP: Target "{current_filename_state}" already exists in "{root}". Cannot rename "{original_filename}".'
                        log_messages.append(log_msg)
                        errors.append(log_msg)
                    else:
                        os.rename(original_path, new_path)
                        log_messages.append(f'RENAMED: "{original_filename}" to "{current_filename_state}" in "{root}".')
                        renamed_count += 1
                except Exception as e:
                    log_msg = f'ERROR: Renaming "{original_filename}" to "{current_filename_state}" failed: {e}'
                    log_messages.append(log_msg)
                    errors.append(log_msg)
            elif not current_filename_state and original_filename: # Original had a name, cleaned is empty
                log_msg = f'WARN: Cleaning "{original_filename}" results in an empty filename. Skipped.'
                log_messages.append(log_msg)
                errors.append(log_msg)
    
    log_messages.append(f"Scan complete. Processed: {processed_count}, Renamed: {renamed_count}, Errors/Warnings: {len(errors)}.")
    return log_messages, renamed_count, processed_count, errors


if __name__ == '__main__':
    # Example usage:
    test_directory_path = r'E:\BaiduNetdiskDownload' # IMPORTANT: Use a test directory!
    print(f"Cleaning filenames in: {test_directory_path}")
    logs, renamed, processed, errors_list = clean_directory_filenames(test_directory_path)
    for log_entry in logs:
        print(log_entry)
    print(f"\nSummary: Processed {processed}, Renamed {renamed}, Errors/Warnings {len(errors_list)}")
