# 项目概览

## 脚本描述

### file_clean_useless_name.py
`file_clean_useless_name.py` 用于清理目录中文件名中的无用字符，如空格、特殊字符、日期等。它可以帮助用户规范文件名，使其更易于识别和管理。

### file_duration_statistics.py
该脚本用于计算指定目录及其子目录中所有 MP4 文件的总时长。它利用 `ffprobe` 工具获取每个视频文件的时长，并将这些时长累加以呈现总时长。

### file_find_duplicates.py
`file_find_duplicates.py` 设计用于通过比较文件哈希值来识别和报告目录中的重复文件。它可以帮助用户快速找到重复的文件，以便进一步处理。

### file_rename.py
`file_rename.py` 提供了一个批量重命名目录中文件的工具，按照指定的模式或规则进行，如添加前缀或后缀，或根据文件的创建日期和时间重命名文件。

### software_quickstart.py
`software_quickstart.py` 用于快速启动指定的软件。它可以帮助用户快速启动常用的软件，而无需手动查找并点击软件图标。

### traditional_to_simplified.py
`traditional_to_simplified.py` 用于将文本文件中的繁体中文转换为简体中文。它利用 `opencc` 工具将文本文件中的繁体中文转换为简体中文。

## 使用方法
每个脚本都可以在其所在目录下通过命令行运行。具体的使用说明已在每个脚本文件中以注释的形式提供。
