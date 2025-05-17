import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import importlib # 用于动态导入

# --- 开始：调整 sys.path 以确保项目根目录可以导入 ---
# 此处假设 main_gui.py位于项目根目录的子目录中（例如 gui_app）。
# project_root 将是 .../toolbox/
_project_root_for_version = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root_for_version not in sys.path:
    sys.path.insert(0, _project_root_for_version)

try:
    from version import __version__, __app_name__
except ImportError:
    # 如果在开发过程中未找到 version.py 或路径不正确，则使用回退值
    __version__ = "Dev"
    __app_name__ = "工具箱应用 (Dev)"
    print("Warning: Could not import version.py. Using development version info.")
# --- 结束：调整 sys.path ---

# 工具框架的导入
# from gui_app.tool_batch_rename import BatchRenameFrame # 动态加载
# from gui_app.tool_video_duration import VideoDurationFrame # 动态加载
# from gui_app.tool_find_duplicates import FindDuplicatesFrame # 动态加载
# from gui_app.tool_software_quickstart import SoftwareQuickstartFrame # 动态加载

# --- 常量 ---
TOOLS_DIR = "gui_app.tools" # 相对于项目根目录，供 importlib 使用
TOOLS_SUB_DIR = "tools" # gui_app 内的子目录名称
PLUGIN_CLASS_NAME = "ToolPluginFrame"
DEFAULT_TOOL_ORDER = 1000

# --- 各工具的UI框架 ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{__app_name__} v{__version__}")
        self.geometry("900x700")
        ctk.set_appearance_mode("System") 
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.nav_panel = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.nav_panel.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)
        # nav_panel 的行配置将在加载工具后设置

        ctk.CTkLabel(self.nav_panel, text="工具选择", font=ctk.CTkFont(size=15, weight="bold"))\
            .grid(row=0, column=0, padx=20, pady=(20, 10))

        self.buttons = {}
        self.frames = {}
        
        # 尽早初始化 right_panel，以便即使没有工具加载，各工具框架也能以它为父容器
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)

        loaded_tools = self._load_tools_from_directory()
        current_nav_row = 1 # 从"工具选择"标签之后开始

        if not loaded_tools:
            ctk.CTkLabel(self.nav_panel, text="未找到任何工具插件！", text_color="orange")\
                .grid(row=current_nav_row, column=0, padx=20, pady=10)
            current_nav_row +=1
            # 如果没有可用的工具，在右侧面板中显示一条消息
            error_label = ctk.CTkLabel(self.right_panel, 
                                       text=("没有可用的工具或工具加载失败。\\n"
                                             "请检查 'gui_app/tools' 目录下的插件。"),
                                       font=ctk.CTkFont(size=16))
            error_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        else:
            loaded_tools.sort(key=lambda x: (x.get('order', DEFAULT_TOOL_ORDER), x['name']))

            for i, tool_info in enumerate(loaded_tools):
                button = ctk.CTkButton(self.nav_panel, text=tool_info['name'], 
                                       command=lambda n=tool_info['name']: self.select_frame_by_name(n))
                button.grid(row=current_nav_row, column=0, padx=20, pady=10, sticky="ew")
                self.buttons[tool_info['name']] = button
                current_nav_row += 1
                
                try:
                    frame_instance = tool_info['class'](self.right_panel)
                    self.frames[tool_info['name']] = frame_instance
                    # 立即网格化成功实例化的框架，如果需要，稍后会将其置顶显示
                    frame_instance.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
                except Exception as e:
                    print(f"Error instantiating frame for tool '{tool_info['name']}': {e}")
                    self.buttons[tool_info['name']].configure(state="disabled", text=f"{tool_info['name']} (错误)")
                    # 对于此键，self.frames[tool_info['name']] 将保持为 None 或未设置

            self.nav_panel.grid_rowconfigure(len(loaded_tools) + 1, weight=1)

            # 选择初始框架（已成功实例化的排序列表中的第一个）
            first_tool_name_to_select = None
            for tool_info in loaded_tools:
                if tool_info['name'] in self.frames and self.frames[tool_info['name']] is not None:
                    first_tool_name_to_select = tool_info['name']
                    break
            
            if first_tool_name_to_select:
                 self.select_frame_by_name(first_tool_name_to_select) 
            elif not self.frames: # 此情况应在之前的 'if not loaded_tools' 中捕获，但作为备用逻辑
                error_label = ctk.CTkLabel(self.right_panel, 
                                       text=("所有工具均加载失败或无法实例化。\\n"
                                             "请检查控制台输出获取更多信息。"),
                                       font=ctk.CTkFont(size=16))
                error_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

            # --- 已添加：更新日志按钮 ---
            # 用于将按钮推到底部的空白间隔，或者直接将其放在工具之后
            # self.nav_panel.grid_rowconfigure(current_nav_row, weight=1) # 可选：如果 current_nav_row 用作间隔索引，则将按钮推到底部
            # current_nav_row += 1 

            self.changelog_button = ctk.CTkButton(self.nav_panel, text="更新日志", command=self.show_changelog_window)
            self.changelog_button.grid(row=current_nav_row, column=0, padx=20, pady=(20,10), sticky="ew") # 顶部 pady 以提供一些空间
            current_nav_row +=1

            # 配置 nav_panel 的最后一行以占据剩余空间，将元素向上推，或者如果上面使用了间隔，则将更新日志按钮推到底部
            self.nav_panel.grid_rowconfigure(current_nav_row, weight=1)

    def _load_tools_from_directory(self):
        loaded_tools_info = []
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 在 PyInstaller 打包环境中运行
            # sys._MEIPASS 是打包后应用的根目录
            # .spec 文件中的 datas 是 ('gui_app/tools', 'gui_app/tools')，因此它被复制到相对于 _MEIPASS 的 'gui_app/tools' 目录下
            tools_fs_path = os.path.join(sys._MEIPASS, 'gui_app', TOOLS_SUB_DIR)
        else:
            # 在正常的 Python 环境中运行
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            tools_fs_path = os.path.join(current_script_dir, TOOLS_SUB_DIR)

        if not os.path.isdir(tools_fs_path):
            print(f"Tools directory not found: {tools_fs_path}")
            return loaded_tools_info

        for filename in os.listdir(tools_fs_path):
            if filename.startswith("tool_") and filename.endswith(".py") and filename != "__init__.py":
                module_name_fs = os.path.splitext(filename)[0]
                module_path_for_import = f"{TOOLS_DIR}.{module_name_fs}"
                
                try:
                    print(f"Attempting to load tool module: {module_path_for_import}")
                    tool_module = importlib.import_module(module_path_for_import)
                    
                    if hasattr(tool_module, PLUGIN_CLASS_NAME):
                        plugin_class = getattr(tool_module, PLUGIN_CLASS_NAME)
                        tool_name = getattr(plugin_class, 'TOOL_NAME', module_name_fs.replace("tool_", "").replace("_", " ").title())
                        tool_order = getattr(plugin_class, 'TOOL_ORDER', DEFAULT_TOOL_ORDER)
                        
                        loaded_tools_info.append({
                            'name': tool_name,
                            'order': tool_order,
                            'class': plugin_class,
                            'module_path': module_path_for_import
                        })
                        print(f"Successfully loaded: {tool_name}")
                    else:
                        print(f"Warning: Module {module_path_for_import} does not have class {PLUGIN_CLASS_NAME}.")
                
                except ImportError as e:
                    print(f"Error importing module {module_path_for_import}: {e}")
                except AttributeError as e:
                    print(f"Error accessing attributes in {module_path_for_import} or its class: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred loading tool from {module_path_for_import}: {e}")
        
        return loaded_tools_info

    def select_frame_by_name(self, name):
        for btn_name, button_widget in self.buttons.items():
            is_selected = (btn_name == name)
            current_fg_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            current_hover_color = getattr(button_widget, '_hover_color', "gray")
            
            if isinstance(current_fg_color, (list, tuple)):
                effective_fg_color = current_fg_color[1] if ctk.get_appearance_mode().lower() == "dark" else current_fg_color[0]
            else:
                effective_fg_color = current_fg_color
            
            is_hovering = getattr(button_widget, '_hover', False)
            button_widget.configure(fg_color=effective_fg_color if is_selected else current_hover_color if is_hovering else "transparent")

        if name in self.frames and self.frames[name] is not None:
            self.frames[name].tkraise()
        else:
            print(f"Error or Frame Not Found: No valid frame configured or instantiated for '{name}'")

    # --- 已添加：显示更新日志窗口的方法 ---
    def show_changelog_window(self):
        changelog_content = "错误: CHANGELOG.md 文件未找到." # 默认错误消息
        
        # 确定数据文件的基本路径
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 在 PyInstaller 打包环境中运行
            base_path = sys._MEIPASS
            # 尝试读取 CHANGELOG.md 的路径
            possible_paths = [
                os.path.join(base_path, "CHANGELOG.md"),
                os.path.join(base_path, "_internal", "CHANGELOG.md")
            ]
        else:
            # 在正常的 Python 环境中运行
            base_path = _project_root_for_version # 在脚本顶部定义
            possible_paths = [os.path.join(base_path, "CHANGELOG.md")]

        for path_to_try in possible_paths:
            try:
                with open(path_to_try, "r", encoding="utf-8") as f:
                    changelog_content = f.read()
                break # 已找到并读取文件，退出循环
            except FileNotFoundError:
                continue # 尝试下一个路径
            except Exception as e:
                changelog_content = f"读取更新日志时发生错误: {e}"
                break # 遇到其他错误则停止

        if hasattr(self, "changelog_win") and self.changelog_win.winfo_exists():
            self.changelog_win.focus()
            return

        self.changelog_win = ctk.CTkToplevel(self)
        self.changelog_win.title("更新日志")
        self.changelog_win.geometry("700x500")
        self.changelog_win.transient(self) # 使其成为主应用的瞬态窗口

        textbox = ctk.CTkTextbox(self.changelog_win, wrap=tk.WORD, activate_scrollbars=True)
        textbox.pack(expand=True, fill="both", padx=10, pady=10)
        textbox.insert("1.0", changelog_content)
        textbox.configure(state="disabled") # 使其只读

        self.changelog_win.after(100, self.changelog_win.lift) # 确保其在顶层
        self.changelog_win.focus_set()

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    app = App()
    app.mainloop() 