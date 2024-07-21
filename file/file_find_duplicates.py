import os
import shutil
import hashlib
from PIL import Image
import imagehash
from collections import defaultdict


def get_file_hash(filepath):
    """根据文件类型计算不同的哈希值"""
    ext = filepath.split('.')[-1].lower()
    if ext in ['png', 'jpg', 'jpeg']:
        return hash_image(filepath)
    elif ext in ['mp4', 'avi', 'mkv']:
        return hash_video(filepath)
    else:
        return None


def hash_image(filepath):
    """计算图片的感知哈希值"""
    with Image.open(filepath) as img:
        img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        hash_value = imagehash.average_hash(img)
    return str(hash_value)


def hash_video(filepath):
    """计算视频文件的SHA256哈希值"""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def find_duplicates(folders):
    """在一个或多个文件夹中查找重复文件"""
    hashes = defaultdict(list)
    for folder in folders:
        for root, _, files in os.walk(folder):
            for file in files:
                path = os.path.join(root, file)
                file_hash = get_file_hash(path)
                if file_hash:
                    hashes[file_hash].append(path)

    duplicates_folder = os.path.join(folders[0], 'duplicates')
    if not os.path.exists(duplicates_folder):
        os.makedirs(duplicates_folder)

    # 分组移动重复文件
    for file_hash, paths in hashes.items():
        if len(paths) > 1:
            group_folder = os.path.join(duplicates_folder, file_hash[:10])
            os.makedirs(group_folder, exist_ok=True)
            for path in paths:
                shutil.move(path, os.path.join(group_folder, os.path.basename(path)))


if __name__ == '__main__':
    # 可以指定单个或多个文件夹
    folders = ['E:\\test']
    find_duplicates(folders)
    print("Duplicate processing complete.")
