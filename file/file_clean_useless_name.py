import os
import re

# 模式在此处全局定义，如果以后需要通过 GUI 配置，则可以作为参数传递
PATTERNS_TO_CLEAN = [
    r'www.zxit8.com_',
    r' - Copy',
    r'\s+(?=\.\w+$)',  # 移除扩展名之前的空格
    r'\d{2}_\d{2}_ev',
    r' \d{4}-\d{2}-\d{2}'
]

def clean_directory_filenames(directory_path, patterns=None, log_callback=None):
    """
    根据正则表达式模式清理指定目录及其子目录中的文件名。
    如果提供，则使用 log_callback 增量输出消息。
    返回所有日志消息的列表、cleaned_count、skipped_count 和 error_count。
    """
    if patterns is None:
        patterns = PATTERNS_TO_CLEAN
    
    processed_count = 0
    cleaned_count = 0
    error_count = 0
    logs = []

    def _log(msg):
        logs.append(msg)
        if log_callback:
            try:
                log_callback(msg)
            except Exception as e:
                logs.append(f"[Callback Error]: {e}")

    if not os.path.isdir(directory_path):
        _log(f"Error: Directory '{directory_path}' not found.")
        # 为了返回签名的一致性，正确计算 skipped_count
        skipped_count = processed_count - cleaned_count - error_count 
        return logs, cleaned_count, skipped_count, error_count

    for root, _, files in os.walk(directory_path):
        for filename in files:
            processed_count += 1
            original_filename = filename
            current_filename_state = filename

            for pattern in patterns:
                current_filename_state = re.sub(pattern, '', current_filename_state)
            
            current_filename_state = current_filename_state.strip()

            if current_filename_state != original_filename and current_filename_state:
                original_path = os.path.join(root, original_filename)
                new_path = os.path.join(root, current_filename_state)
                try:
                    if os.path.exists(new_path) and original_path.lower() != new_path.lower():
                        _log(f'SKIP: Target "{current_filename_state}" already exists in "{root}". Cannot rename "{original_filename}".')
                    else:
                        os.rename(original_path, new_path)
                        _log(f'RENAMED: "{original_filename}" to "{current_filename_state}" in "{root}".')
                        cleaned_count += 1
                except Exception as e:
                    _log(f'ERROR: Renaming "{original_filename}" to "{current_filename_state}" failed: {e}')
                    error_count += 1
            elif not current_filename_state and original_filename: # 原始名称存在，清理后为空
                _log(f'WARN: Cleaning "{original_filename}" results in an empty filename. Skipped.')
                # 考虑到发生错误/警告的情况，如果符合你的定义，则对其进行计数
                # 目前，为了摘要的目的，我们将其计为一个错误，因为它是一个不希望的结果。
                error_count +=1 # 或者，如果需要更细的粒度，可以使用像 'warning_count' 这样的新类别
            # 未重命名且未导致错误/警告的文件被隐式跳过/视为正常。
    
    summary_message = f"Scan complete. Processed: {processed_count}, Cleaned: {cleaned_count}, Errors/Warnings: {error_count}."
    _log(summary_message) # 同时记录最终摘要
    
    # 根据已处理、已清理和错误数计算 skipped_count
    # 此处的 skipped_count 指的是已处理但既未清理也未导致错误的文件。
    skipped_count = processed_count - cleaned_count - error_count
    if skipped_count < 0: skipped_count = 0 # 确保为非负数，尽管逻辑上不应如此。

    return logs, cleaned_count, skipped_count, error_count


if __name__ == '__main__':
    # 示例用法：
    test_directory_path = r'E:\\BaiduNetdiskDownload' # 重要：请使用测试目录！
    print(f"Cleaning filenames in: {test_directory_path}")
    
    # 使用 log_callback 的示例（例如，用于控制台测试的 print 函数）
    def console_logger(message):
        print(f"CALLBACK_LOG: {message}")

    # logs, cleaned, skipped, errors_list = clean_directory_filenames(test_directory_path) # 不使用回调
    logs, cleaned, skipped, errors_list = clean_directory_filenames(test_directory_path, log_callback=console_logger) # 使用回调
    
    # 如果你需要独立于回调输出的消息，'logs' 将包含所有消息
    # print("\\n--- 所有收集到的日志：---")
    # for log_entry in logs:
    #     print(log_entry)
    
    print(f"\nSummary from return values: Cleaned {cleaned}, Skipped/No Change {skipped}, Errors/Warnings {errors_list}")
