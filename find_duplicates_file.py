import hashlib
import os


def hash_fine(filepath):
    """计算文件的SHA256哈希值"""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)  # 读取大文件的较大快以减少内存消耗
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def find_duplicates(directory):
    """在给定的目录中查找重复文件"""
    hashes = {}
    duplicates = []

    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, filename)):
            file_path = os.path.join(directory, filename)
            # 计算文件的哈希值
            file_hash = hash_fine(file_path)

            # 如果哈希值已经存在，则说明文件重复
            if file_hash in hashes:
                duplicates.append((file_path, hashes[file_hash]))
            else:
                hashes[file_hash] = filename

    return duplicates


if __name__ == '__main__':
    # 指定包含视频文件的目录
    directory = 'E:\\test'
    duplicates = find_duplicates(directory)

    if len(duplicates) > 0:
        # 打印所有重复文件的路径
        for file1, file2 in duplicates:
            print(f"Duplicate files: {file1} {file2}")
    else:
        print("No duplicate files found.")
