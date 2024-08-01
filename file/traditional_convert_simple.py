import os
from opencc import OpenCC


def convert_srt_to_simple_chinese(input_folder):
    cc = OpenCC('t2s')

    #  确保输入文件存在
    if not os.path.exists(input_folder):
        print("指定的文件夹不存在")
        return

    # 遍历文件夹中的所有文件
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.srt'):
            input_file = os.path.join(input_folder, file_name)
            output_file = os.path.join(input_folder, f'simple_{file_name}')

            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                with open(output_file, 'w', encoding='utf-8') as f:
                    for line in lines:
                        # 转换每一行并写入新文件
                        simple_chinese_txt = cc.convert(line)
                        f.write(cc.convert(simple_chinese_txt))

                print(f"转换完成。简体中文字幕已保存到：{output_file}")
            except Exception as e:
                print(f"处理文件时出错：{e}")


if __name__ == '__main__':
    input_folder = r'E:\test'
    convert_srt_to_simple_chinese(input_folder)
