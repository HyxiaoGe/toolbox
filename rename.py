import os
def rename_files(folder_path, new_name):
    # 初始化一个计数器，从1开始
    counter = 1

    # 遍历指定目标文件夹中的所有文件
    for filename in os.listdir(folder_path):
        # 检查目标是否是一个文件，而不是文件夹
        if not os.path.isdir(os.path.join(folder_path, filename)):
            # 获取文件的扩展名
            file_extension = os.path.splitext(filename)[1]
            # 生成新文件名，格式为：新名字 + 索引 + 扩展名
            new_filename = f"{new_name}{counter}{file_extension}"
            # 重命名文件
            os.rename(os.path.join(folder_path, filename), os.path.join(folder_path, new_filename))
            print(f"Rename {filename} to {new_filename}")
            # 计数器加1
            counter += 1

if __name__ == '__main__':
    # 文件夹路径
    folder_path = 'E:\\test'
    # 前缀字符串，可以根据需要修改
    prefix = 'test_'
    # 调用函数
    rename_files(folder_path, prefix)