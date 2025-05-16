import os
import shutil
import hashlib
from PIL import Image
import imagehash
from collections import defaultdict
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def hash_generic_file(filepath):
    """计算通用文件的SHA256哈希值 (基于完整内容)"""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536) # Read in 64KB chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except FileNotFoundError:
        logging.error(f"File not found during generic hashing: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Could not hash generic file {filepath}: {e}")
        return None


def get_file_hash(filepath):
    """根据文件类型计算不同的哈希值"""
    ext = filepath.split('.')[-1].lower()
    if ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff']: # Added more image types
        return hash_image(filepath)
    elif ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv']: # Added more video types
        return hash_video(filepath)
    else:
        # logging.debug(f"Using generic hash for: {filepath} (type: {ext})")
        return hash_generic_file(filepath) # Fallback to generic full-file hash


def hash_image(filepath):
    """计算图片的感知哈希值"""
    try:
        with Image.open(filepath) as img:
            # Convert to L mode (grayscale) for perceptual hash
            # Resize to a small, fixed size (e.g., 8x8 or 16x16)
            # Image.Resampling.LANCZOS is a high-quality downsampling filter
            img_hash = imagehash.average_hash(img.convert("L").resize((16, 16), Image.Resampling.LANCZOS))
        return str(img_hash)
    except Exception as e:
        # logging.error(f"Could not hash image {filepath}: {e}")
        return None


def hash_video(filepath, sample_size_mb=5):
    """计算视频文件部分内容的SHA256哈希值，以提高速度"""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            # Read a sample from the beginning, middle, and end of the file
            file_size = os.path.getsize(filepath)
            chunk_size = 65536  # 64KB
            sample_bytes = sample_size_mb * 1024 * 1024

            if file_size <= sample_bytes: # If file is small, hash the whole thing
                buf = f.read(chunk_size)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(chunk_size)
            else:
                # Sample beginning
                for _ in range(sample_bytes // (3 * chunk_size) if sample_bytes // (3 * chunk_size) > 0 else 1):
                    buf = f.read(chunk_size)
                    if not buf: break
                    hasher.update(buf)
                
                # Sample middle
                f.seek(file_size // 2 - (sample_bytes // (6 * chunk_size) * chunk_size) if file_size // 2 - (sample_bytes // (6 * chunk_size) * chunk_size) > 0 else file_size // 2 )
                for _ in range(sample_bytes // (3 * chunk_size) if sample_bytes // (3 * chunk_size) > 0 else 1):
                    buf = f.read(chunk_size)
                    if not buf: break
                    hasher.update(buf)

                # Sample end
                f.seek(file_size - (sample_bytes // (3 * chunk_size) * chunk_size) if file_size - (sample_bytes // (3 * chunk_size) * chunk_size) > sample_bytes else file_size - sample_bytes) # ensure we read from a valid position
                for _ in range(sample_bytes // (3 * chunk_size) if sample_bytes // (3 * chunk_size) > 0 else 1):
                    buf = f.read(chunk_size)
                    if not buf: break
                    hasher.update(buf)
        return hasher.hexdigest()
    except FileNotFoundError:
        # logging.error(f"File not found during video hashing: {filepath}")
        return None
    except Exception as e:
        # logging.error(f"Could not hash video {filepath}: {e}")
        return None


def collect_duplicate_files_info(directory_path):
    """
    在一个文件夹中查找重复文件信息，但不移动它们。
    返回一个字典，键是哈希值，值是具有该哈希值的文件路径列表。
    仅包含实际的重复项（即，每个哈希至少有两个文件）。
    还会返回日志。
    """
    hashes = defaultdict(list)
    logs = []
    processed_files = 0
    skipped_unsupported = 0
    skipped_hash_errors = 0

    if not os.path.isdir(directory_path):
        logs.append(f"错误: 提供的路径不是一个有效的目录: {directory_path}")
        return {}, logs, processed_files, skipped_unsupported, skipped_hash_errors

    logs.append(f"开始扫描目录: {directory_path}")
    for root, _, files in os.walk(directory_path):
        for file in files:
            processed_files += 1
            path = os.path.join(root, file)
            if os.path.isfile(path): # Ensure it's a file
                # logs.append(f"正在处理: {path}")
                file_hash = get_file_hash(path)
                if file_hash:
                    hashes[file_hash].append(path)
                elif file_hash is None and get_file_hash.__doc__.count(path.split('.')[-1].lower()) == 0 : # check if it was unsupported
                    skipped_unsupported +=1
                    logs.append(f"跳过不支持的文件类型: {path}")
                else: # Error during hashing
                    skipped_hash_errors +=1
                    logs.append(f"警告: 无法计算哈希值 {path}")


    duplicate_groups = {hash_val: paths for hash_val, paths in hashes.items() if len(paths) > 1}
    
    num_duplicate_groups = len(duplicate_groups)
    num_duplicate_files = sum(len(paths) for paths in duplicate_groups.values())

    logs.append(f"扫描完成。处理了 {processed_files} 个文件。")
    logs.append(f"跳过了 {skipped_unsupported} 个不支持的文件类型。")
    logs.append(f"跳过了 {skipped_hash_errors} 个文件（哈希计算错误）。")
    if num_duplicate_groups > 0:
        logs.append(f"找到了 {num_duplicate_groups} 组重复文件，共涉及 {num_duplicate_files} 个文件。")
    else:
        logs.append("未找到重复文件。")
        
    return duplicate_groups, logs, processed_files, skipped_unsupported, skipped_hash_errors


def move_files_to_duplicate_folder(duplicate_groups, base_folder_for_duplicates_dir):
    """
    将 collect_duplicate_files_info 识别出的重复文件移动到指定的 'duplicates' 文件夹结构中。
    'duplicates' 文件夹将在 base_folder_for_duplicates_dir 内创建。
    """
    logs = []
    moved_files_count = 0
    if not duplicate_groups:
        logs.append("没有重复文件组可供移动。")
        return logs, moved_files_count

    # Ensure base_folder_for_duplicates_dir is a directory, not a file path from within the scan
    # It should be the same as the initially scanned directory by the user.
    if not os.path.isdir(base_folder_for_duplicates_dir):
        logs.append(f"错误: 用于创建 'duplicates' 文件夹的基础路径无效: {base_folder_for_duplicates_dir}")
        return logs, moved_files_count

    duplicates_main_folder = os.path.join(base_folder_for_duplicates_dir, 'duplicates_found') # Renamed to avoid conflict with a potential 'duplicates' file
    
    try:
        if not os.path.exists(duplicates_main_folder):
            os.makedirs(duplicates_main_folder)
            logs.append(f"创建主重复文件夹: {duplicates_main_folder}")
        else:
            logs.append(f"主重复文件夹已存在: {duplicates_main_folder}")

        for file_hash, paths in duplicate_groups.items():
            if len(paths) > 1: # Should always be true due to how duplicate_groups is constructed
                # Create a subfolder for this group of duplicates, named after the hash (or part of it)
                group_folder_name = file_hash[:12].replace("/", "_").replace("\\", "_") # Make sure hash is filename-safe
                group_folder_path = os.path.join(duplicates_main_folder, group_folder_name)
                
                if not os.path.exists(group_folder_path):
                    os.makedirs(group_folder_path)
                    logs.append(f"  为哈希 {file_hash[:12]} 创建子文件夹: {group_folder_path}")

                for path in paths:
                    if os.path.exists(path): # Check if file still exists (e.g. not moved by another process)
                        try:
                            destination_filename = os.path.basename(path)
                            destination_path = os.path.join(group_folder_path, destination_filename)
                            
                            # Handle potential filename conflicts in the destination
                            counter = 1
                            original_destination_path = destination_path
                            while os.path.exists(destination_path):
                                name, ext = os.path.splitext(destination_filename)
                                destination_path = os.path.join(group_folder_path, f"{name}_{counter}{ext}")
                                counter += 1
                            if original_destination_path != destination_path:
                                logs.append(f"    注意: 目标文件名冲突，'{os.path.basename(original_destination_path)}' 将作为 '{os.path.basename(destination_path)}' 保存。")

                            shutil.move(path, destination_path)
                            logs.append(f"    已移动: '{path}' 到 '{destination_path}'")
                            moved_files_count += 1
                        except Exception as e_move:
                            logs.append(f"    错误: 移动文件 '{path}' 失败: {e_move}")
                    else:
                        logs.append(f"    警告: 文件 '{path}' 在尝试移动前未找到。可能已被删除或移动。")
        
        if moved_files_count > 0:
            logs.append(f"文件移动完成。共移动 {moved_files_count} 个文件。")
        else:
            logs.append("没有文件被移动（可能所有文件都无法访问或移动过程中出错）。")

    except Exception as e_main:
        logs.append(f"创建重复文件夹或移动文件时发生严重错误: {e_main}")
        
    return logs, moved_files_count


# 保留原始的 find_duplicates 函数，但现在它将使用新的辅助函数
# 或者我们可以弃用它，让GUI直接调用 collect 和可选的 move
def find_duplicates_and_move(folders_to_scan, move_them=False): # Added move_them flag
    """
    在一个或多个文件夹中查找重复文件。
    如果 move_them 为 True，则会将重复文件移动到第一个文件夹下的 'duplicates_found' 子目录中。
    """
    all_logs = []
    all_duplicate_groups = {}
    
    if not folders_to_scan:
        all_logs.append("错误: 未提供要扫描的文件夹。")
        return all_logs, {}

    primary_scan_folder = folders_to_scan[0] # Used as base for 'duplicates_found' directory

    for folder_path in folders_to_scan:
        all_logs.append(f"--- 开始处理文件夹: {folder_path} ---")
        duplicate_groups, logs, _, _, _ = collect_duplicate_files_info(folder_path)
        all_logs.extend(logs)
        
        # Merge results - simple merge, could be smarter if hashes collide across folders but unlikely for content hashes
        for hash_val, paths in duplicate_groups.items():
            if hash_val not in all_duplicate_groups:
                all_duplicate_groups[hash_val] = []
            all_duplicate_groups[hash_val].extend(paths) # Extend to keep all paths

    # Filter again in case merging paths made some groups non-duplicates (if files were identical across folders)
    # This logic might need refinement depending on desired behavior for duplicates *across* multiple input folders.
    # For now, any file appearing more than once in the *combined* list for a hash is a duplicate.
    final_duplicate_groups = {
        hash_val: list(set(paths)) for hash_val, paths in all_duplicate_groups.items() if len(list(set(paths))) > 1
    }


    if not final_duplicate_groups:
        all_logs.append("所有扫描的文件夹中均未找到重复文件。")
    else:
        num_groups = len(final_duplicate_groups)
        num_files = sum(len(paths) for paths in final_duplicate_groups.values())
        all_logs.append(f"在所有文件夹中总共找到 {num_groups} 组重复文件，涉及 {num_files} 个文件。")

        if move_them:
            all_logs.append(f"--- 开始移动重复文件到 '{os.path.join(primary_scan_folder, 'duplicates_found')}' ---")
            move_logs, moved_count = move_files_to_duplicate_folder(final_duplicate_groups, primary_scan_folder)
            all_logs.extend(move_logs)
            all_logs.append(f"总共移动了 {moved_count} 个文件。")
        else:
            all_logs.append("未执行文件移动操作（move_them=False）。")
            all_logs.append("重复文件详情:")
            for hash_val, paths in final_duplicate_groups.items():
                all_logs.append(f"  哈希: {hash_val[:12]}... ({len(paths)} 个文件):")
                for p in paths:
                    all_logs.append(f"    - {p}")
                    
    return all_logs, final_duplicate_groups


if __name__ == '__main__':
    # 可以指定单个或多个文件夹
    test_folders = ['E:\\test_duplicates_1', 'E:\\test_duplicates_2'] # Example folders
    # Create some dummy files for testing
    # os.makedirs(test_folders[0], exist_ok=True)
    # os.makedirs(test_folders[1], exist_ok=True)
    # with open(os.path.join(test_folders[0], "img1.png"), "wb") as f: f.write(os.urandom(1024)) # dummy image data
    # with open(os.path.join(test_folders[0], "img1_copy.png"), "wb") as f: f.write(open(os.path.join(test_folders[0], "img1.png"),"rb").read())
    # with open(os.path.join(test_folders[0], "vid1.mp4"), "wb") as f: f.write(os.urandom(1024*1024)) # dummy video data
    # with open(os.path.join(test_folders[1], "vid1_moved.mp4"), "wb") as f: f.write(open(os.path.join(test_folders[0], "vid1.mp4"),"rb").read())
    # with open(os.path.join(test_folders[1], "unique_img.jpg"), "wb") as f: f.write(os.urandom(512))

    # logs, duplicates = collect_duplicate_files_info(test_folders[0])
    # print("\n--- Collection Logs ---")
    # for log_entry in logs:
    # print(log_entry)
    # print("\n--- Found Duplicates ---")
    # for hash_val, paths in duplicates.items():
    # print(f"Hash: {hash_val}")
    # for path in paths:
    # print(f"  - {path}")

    # if duplicates:
    # print("\n--- Moving Files (simulation) ---")
    #     # move_logs, moved_count = move_files_to_duplicate_folder(duplicates, test_folders[0])
    #     # for log_entry in move_logs:
    #     # print(log_entry)
    #     # print(f"Total files moved: {moved_count}")
    # else:
    # print("\nNo duplicates found to move.")
    
    # Test the combined function
    # Set move_them=True to actually move files, False to just list them.
    # Ensure 'E:\test_duplicates_1' and 'E:\test_duplicates_2' exist or change paths.
    # For safety, backup test folders before running with move_them=True.
    if os.path.exists('E:\\test_duplicates_1'): # Guard for safety
        print(f"测试 find_duplicates_and_move (move_them=False):")
        logs_report, dupe_groups_report = find_duplicates_and_move(['E:\\test_duplicates_1'], move_them=False)
        for entry in logs_report:
            print(entry)
        
        # print(f"\n\nTesting find_duplicates_and_move (move_them=True):") # UNCOMMENT WITH CAUTION
        # logs_report_move, _ = find_duplicates_and_move(['E:\\test_duplicates_1'], move_them=True)
        # for entry in logs_report_move:
        #     print(entry)
    else:
        print("测试文件夹 E:\\test_duplicates_1 不存在，跳过 __main__ 中的测试。")
