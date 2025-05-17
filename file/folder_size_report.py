import os

def human_readable_size(size_bytes, decimal_places=2):
    if size_bytes is None: # 处理无法确定大小的情况
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.{decimal_places}f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.{decimal_places}f} PB" # 这里应该是 size_bytes

def get_folder_size_recursive(path, log_callback=None):
    """
    递归计算文件夹及其内容的总大小。
    返回 (总大小_字节, 日志列表, 错误列表)
    logs_list 包含详细信息，errors_list 包含错误消息。
    """
    total_size = 0
    logs = []
    errors = []
    # 内部辅助函数，避免重复检查 log_callback
    def _log(message, is_error=False):
        if is_error:
            errors.append(message)
        logs.append(message)
        if log_callback:
            try:
                log_callback(message)
            except Exception as e_cb:
                logs.append(f"[Log Callback Error]: {e_cb}") # 将回调错误记录到主日志
                pass # 不要让回调错误停止进程

    if not os.path.isdir(path):
        _log(f"警告: 提供的路径不是有效目录: {path}", is_error=True)
        return 0, logs, errors

    for root, dirs, files in os.walk(path, topdown=True, onerror=None): # onerror=None 以尝试在某些错误后继续
        accessible_dirs = []
        for d in dirs: # 在通过 os.walk 进一步递归之前检查子目录的可访问性
            dir_path = os.path.join(root, d)
            if not os.access(dir_path, os.R_OK | os.X_OK):
                _log(f"警告: 无法访问子目录 {dir_path} (权限不足)，已跳过。", is_error=True)
            else:
                accessible_dirs.append(d)
        dirs[:] = accessible_dirs # 原地修改 dirs 供 os.walk 使用

        for f_name in files:
            file_path = os.path.join(root, f_name)
            try:
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    # _log(f"  包含文件: {file_path}, 大小: {size} bytes") # 可能过于冗长
            except FileNotFoundError:
                _log(f"警告: 文件在统计大小期间未找到: {file_path}", is_error=True)
            except PermissionError:
                _log(f"警告: 无法访问文件 {file_path} (权限不足)。", is_error=True)
            except OSError as e_os:
                 _log(f"警告: 读取文件 {file_path} 时发生OS错误: {e_os}", is_error=True)
        
        # Log after processing each directory level within the walk if needed
        # _log(f"完成扫描级别: {root}, 当前累计大小: {total_size} bytes")

    _log(f"完成递归扫描 '{os.path.basename(path)}', 总大小: {total_size} bytes ({human_readable_size(total_size)}). 错误数: {len(errors)}")
    return total_size, logs, errors

def get_subfolder_stats(base_path, log_callback=None):
    """
    列出 base_path 下直接子文件夹的大小。
    返回 (子文件夹数据, 摘要日志, 总体错误列表)
    subfolders_data 是元组列表: (名称, 大小_字节, 可读大小, 状态消息)
    """
    subfolders_results = []
    summary_logs = []
    overall_errors = []

    def _log_summary(message, is_error=False):
        if is_error:
            overall_errors.append(message)
        summary_logs.append(message)
        if log_callback:
            try:
                log_callback(message)
            except Exception as e_cb:
                summary_logs.append(f"[Log Callback Error]: {e_cb}")
                pass 

    _log_summary(f"开始统计根目录: {base_path}")

    if not os.path.isdir(base_path):
        _log_summary(f"错误: 根目录路径无效: {base_path}", is_error=True)
        return [], summary_logs, overall_errors

    try:
        with os.scandir(base_path) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False): # 对于顶级文件夹列表，不跟踪符号链接
                    folder_name = entry.name
                    folder_full_path = os.path.join(base_path, folder_name)
                    _log_summary(f"开始扫描子目录: {folder_name} ...")
                    
                    # 对于每个子文件夹，调用递归大小计算器
                    size_bytes, item_logs, item_errors = get_folder_size_recursive(folder_full_path, log_callback)
                    
                    # 如果需要，将项目扫描中的日志和错误添加到总体日志中，或者仅依赖回调
                    # 对于 GUI，回调是主要的。对于脚本使用，这些也可以返回。
                    # summary_logs.extend([f"  [{folder_name}] {log}" for log in item_logs]) # 可选的详细日志记录
                    overall_errors.extend([f"  [{folder_name}] {err}" for err in item_errors])

                    status_msg = "完成"
                    if item_errors:
                        status_msg = f"完成但有 {len(item_errors)} 个内部错误/警告"
                    
                    if size_bytes is None: # 对于当前在出错时返回 0 的 get_folder_size_recursive 不应发生这种情况
                        size_bytes = 0 
                        status_msg = "错误: 无法计算大小"
                        overall_errors.append(f"无法确定 '{folder_name}' 的大小。")

                    readable = human_readable_size(size_bytes)
                    subfolders_results.append((folder_name, size_bytes, readable, status_msg))
                    _log_summary(f"子目录 '{folder_name}' 统计完成. 大小: {readable}. 状态: {status_msg}")
                elif entry.is_file(follow_symlinks=False):
                    # 可选地，直接在 base_path 中汇总文件大小
                    pass # 目前仅关注子文件夹大小

    except PermissionError as e_perm:
        _log_summary(f"错误: 无法访问根目录 '{base_path}' (权限不足): {e_perm}", is_error=True)
        return [], summary_logs, overall_errors
    except Exception as e_scan:
        _log_summary(f"扫描根目录 '{base_path}' 时发生意外错误: {e_scan}", is_error=True)
        return [], summary_logs, overall_errors

    # 按大小降序排序，错误/None 大小的项排在底部
    subfolders_results.sort(key=lambda x: (x[1] is None, -float('inf') if x[1] is None else -x[1]))

    _log_summary(f"所有子目录统计完成。共处理 {len(subfolders_results)} 个子目录。总错误/警告数: {len(overall_errors)}。")
    return subfolders_results, summary_logs, overall_errors


if __name__ == "__main__":
    target_directory = r"C:\\Users\\18889\\AppData\\Roaming" 
    # target_directory = r"E:\\PythonProject" # 可能具有较少权限问题的示例
    print(f"--- 开始文件夹大小统计测试 ---") 
    print(f"目标: {target_directory}\\n")

    # 定义一个简单的回调以进行测试，该回调将打印到控制台
    def console_logger(message):
        print(f"LOG_CALLBACK: {message}")

    results, logs, errors = get_subfolder_stats(target_directory, log_callback=console_logger)

    print("\n--- Main Script Summary Logs ---")
    for log_msg in logs:
        print(log_msg)
    
    print("\n--- Errors Reported by Main Script (if any) ---")
    if errors:
        for err_msg in errors:
            print(err_msg)
    else:
        print("(无主要错误)")

    print("\n--- Subfolder Statistics Results ---")
    if results:
        print(f"{'子目录名':<40} | {'大小':<15} | {'状态':<30}")
        print("-" * 85)
        for name, size_b, readable_s, status in results:
            print(f"{name:<40} | {readable_s:<15} | {status:<30}")
    else:
        print("未能获取任何子文件夹的统计数据。")
    
    print("\n--- 测试结束 ---")
