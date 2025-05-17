import json
import os

CONFIG_DIR_NAME = ".ToolboxApp"
CONFIG_FILE_NAME = "toolbox_config.json"

def _get_config_file_path():
    """获取配置文件的完整路径，如果目录不存在则创建它。"""
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, CONFIG_DIR_NAME)
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError as e:
            print(f"警告: 无法创建配置目录 {config_dir}: {e}")
            # 如果用户主目录不可写，则回退到当前工作目录
            # 这对于已安装的应用来说不是理想情况，但可能适用于开发环境。
            print(f"将尝试在当前工作目录下创建配置文件。")
            config_dir = os.path.join(os.getcwd(), CONFIG_DIR_NAME)
            if not os.path.exists(config_dir):
                 os.makedirs(config_dir, exist_ok=True) # exist_ok 用于回退路径创建
    return os.path.join(config_dir, CONFIG_FILE_NAME)

CONFIG_FILE_PATH = _get_config_file_path()

def load_config():
    """从JSON文件加载配置。"""
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"警告: 读取配置文件 {CONFIG_FILE_PATH} 失败: {e}")
        return {}

def save_config(config_data):
    """将配置数据保存到JSON文件。"""
    try:
        # 确保目录存在，特别是当使用了回退路径且初始未创建时
        config_dir = os.path.dirname(CONFIG_FILE_PATH)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"错误: 保存配置文件 {CONFIG_FILE_PATH} 失败: {e}")

def get_setting(tool_name, setting_key, default_value=None):
    """获取特定工具的配置项。"""
    config = load_config()
    return config.get(tool_name, {}).get(setting_key, default_value)

def set_setting(tool_name, setting_key, value):
    """设置特定工具的配置项并保存。"""
    config = load_config()
    if tool_name not in config:
        config[tool_name] = {}
    config[tool_name][setting_key] = value
    save_config(config)

if __name__ == '__main__':
    # 一些简单的测试
    print(f"配置文件路径: {CONFIG_FILE_PATH}")

    # 测试设置
    set_setting("TestTool", "username", "test_user")
    set_setting("TestTool", "theme", "dark")
    set_setting("AnotherTool", "last_path", "/some/path")

    # 测试获取
    username = get_setting("TestTool", "username")
    print(f"TestTool username: {username}")

    theme = get_setting("TestTool", "theme")
    print(f"TestTool theme: {theme}")

    last_path = get_setting("AnotherTool", "last_path")
    print(f"AnotherTool last_path: {last_path}")

    non_existent = get_setting("TestTool", "non_existent_key", "default_value_for_non_existent")
    print(f"TestTool non_existent_key: {non_existent}")
    
    non_existent_tool = get_setting("NonExistentTool", "some_key", "default_for_tool")
    print(f"NonExistentTool some_key: {non_existent_tool}")

    config_after_sets = load_config()
    print(f"完整配置内容:\n{json.dumps(config_after_sets, indent=4, ensure_ascii=False)}")

    # 清理测试 (可选)
    # set_setting("TestTool", "username", None) # 用于移除
    # set_setting("TestTool", "theme", None)
    # config = load_config()
    # if "TestTool" in config and not config["TestTool"]:
    #     del config["TestTool"]
    # if "AnotherTool" in config: # 假设我们想要移除它
    #     del config["AnotherTool"]
    # save_config(config)
    # print("清理后的配置:", load_config()) 