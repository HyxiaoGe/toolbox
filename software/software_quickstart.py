import subprocess
import os


def open_file(software_executable_path, file_path):
    try:
        subprocess.Popen([software_executable_path, file_path])
        print("请稍后，文件启动中...")
    except Exception as e:
        print(f"Failed to open file: {e}")


def open_file_default(file_path):
    try:
        os.startfile(file_path)
        print("请稍后，文件启动中...")
    except Exception as e:
        print(f"Failed to open file: {e}")


if __name__ == '__main__':
    software_executable_path = r"E:\WPS Office\ksolaunch.exe"

    file_path = r"C:\Users\18889\Desktop\装备进度表.xls"

    # open_file(software_executable_path, file_path)
    open_file_default(file_path)
