from opencc import OpenCC
import os


def convert_srt_to_simple_chinese(input_file, output_file):
    cc = OpenCC('t2s')

    #  确保输入文件存在
    if not os.path.exists(input_file):
        print("输入文件不存在")
        return

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
    input_srt = r'E:\test\test.srt'
    output_srt = r'E:\test\newtest.srt'

    convert_srt_to_simple_chinese(input_srt, output_srt)
