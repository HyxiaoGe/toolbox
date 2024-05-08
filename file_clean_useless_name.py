import os
import re


def clean_filenames(directory_path):
    # 定义要去除的模式
    patterns = [
        r' - Copy',  # 去除“ - Copy”
        r'\s+(?=\.\w+$)',  # 去除文件扩展名前的空格
        r'\d{2}_\d{2}_ev',  # 去除类似“01_01_ev”的格式
        r' \d{4}-\d{2}-\d{2}'  # 去除类似“-2020-07-07”的日期格式
    ]

    # 遍历指定目录下的所有文件
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            original_filename = filename
            # 对于每个模式，使用正则表达式替换为空
            for pattern in patterns:
                filename = re.sub(pattern, '', filename)

            # 重命名文件
            if filename != original_filename:
                original_path = os.path.join(root, original_filename)
                new_path = os.path.join(root, filename)
                os.rename(original_path, new_path)
                print(f'Renamed "{original_filename}" to "{filename}"')


if __name__ == '__main__':
    directory_path = r'E:\course\Netty'
    clean_filenames(directory_path)
