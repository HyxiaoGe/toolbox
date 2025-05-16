import os

def rename_files_in_directory(folder_path, new_name_prefix):
    """
    Renames files in the specified folder to 'new_name_prefix[counter].original_extension'.
    Returns a list of log messages, count of renamed files, and a list of errors.
    """
    log_messages = []
    renamed_count = 0
    error_list = []
    counter = 1

    if not os.path.isdir(folder_path):
        log_messages.append(f"错误: 文件夹 '{folder_path}' 不存在或无效。")
        return log_messages, renamed_count, error_list

    try:
        filenames = os.listdir(folder_path)
        # Sort filenames to ensure a somewhat consistent renaming order, though this is not strictly guaranteed
        # if other processes are modifying the directory. For user-facing tools, it's good practice.
        filenames.sort() 

        for filename in filenames:
            original_file_path = os.path.join(folder_path, filename)
            if not os.path.isdir(original_file_path):
                try:
                    file_extension = os.path.splitext(filename)[1]
                    # Loop to find a unique new filename if conflicts occur
                    temp_counter = counter
                    while True:
                        new_filename_generated = f"{new_name_prefix}{temp_counter}{file_extension}"
                        new_file_path = os.path.join(folder_path, new_filename_generated)
                        if not os.path.exists(new_file_path) or original_file_path.lower() == new_file_path.lower():
                            break
                        temp_counter += 1
                    
                    if temp_counter != counter:
                        log_messages.append(f"  注意: 为 '{filename}' 生成新名称时跳过计数器值，使用 '{new_filename_generated}'.")
                    actual_counter_used = temp_counter
                    
                    final_new_name = f"{new_name_prefix}{actual_counter_used}{file_extension}"
                    final_new_path = os.path.join(folder_path, final_new_name)
                    
                    # Ensure the actual_counter_used is what gets the file, and that it's truly unique before rename
                    if os.path.exists(final_new_path) and original_file_path.lower() != final_new_path.lower():
                         # This case should ideally be rare due to the while loop, but as a safeguard:
                        err_msg = f"  错误: 目标文件名 '{final_new_name}' 已存在且与原文件不同，跳过 '{filename}'."
                        log_messages.append(err_msg)
                        error_list.append(err_msg)
                        continue # Skip to next file in the outer loop

                    os.rename(original_file_path, final_new_path)
                    log_messages.append(f"  已重命名 '{filename}' 为 '{final_new_name}'.")
                    renamed_count += 1
                    counter = actual_counter_used + 1 # Ensure next default counter is after the one used

                except Exception as e_rename:
                    err_msg = f"  重命名 '{filename}' 失败: {e_rename}"
                    log_messages.append(err_msg)
                    error_list.append(err_msg)
        
        summary_msg = f"批量重命名完成。共重命名 {renamed_count} 个文件。"
        if error_list:
            summary_msg += f" 发生 {len(error_list)} 个错误。"
        log_messages.append(summary_msg)
        return log_messages, renamed_count, error_list

    except Exception as e_list:
        log_messages.append(f"列出或处理文件夹 '{folder_path}' 中的文件时出错: {e_list}")
        return log_messages, renamed_count, error_list


if __name__ == '__main__':
    test_folder_path = r'E:\test_rename' # 使用专门的测试文件夹!
    test_prefix = 'MyFile_'
    
    # 创建一些测试文件
    if not os.path.exists(test_folder_path):
        os.makedirs(test_folder_path)
    for i in range(5):
        with open(os.path.join(test_folder_path, f"original_doc_{i+1}.txt"), 'w') as f:
            f.write(f"This is test file {i+1}")
    with open(os.path.join(test_folder_path, f"MyFile_1.txt"), 'w') as f: # Pre-existing conflicting name
            f.write("This is a pre-existing conflicting file.")

    print(f"开始重命名文件夹 '{test_folder_path}' 内的文件，使用前缀 '{test_prefix}':")
    logs, num_renamed, errors = rename_files_in_directory(test_folder_path, test_prefix)
    for log_entry in logs:
        print(log_entry)
    print(f"\n总结: 重命名了 {num_renamed} 个文件，发生 {len(errors)} 个错误。")

    # 清理测试文件 (可选)
    # import shutil
    # if os.path.exists(test_folder_path):
    #     shutil.rmtree(test_folder_path)
    # print(f"测试文件夹 '{test_folder_path}' 已清理。")