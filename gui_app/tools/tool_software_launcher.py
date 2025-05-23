import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

from gui_app.config_manager import get_setting, set_setting

import subprocess

TOOL_CONFIG_NAME = "SoftwareLauncherTool"
CONFIG_KEY_SHORTCUTS = "shortcuts_list"


class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "软件快捷启动"
    TOOL_ORDER = 60

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 

        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(1, weight=1)

        self.add_shortcut_button = ctk.CTkButton(control_frame, text="添加快捷方式", command=self._add_shortcut_dialog)
        self.add_shortcut_button.grid(row=0, column=0, padx=(0,10), pady=5, sticky="w")

        self.status_var = tk.StringVar(value="点击 '添加快捷方式' 来创建新的启动项.")
        self.status_label = ctk.CTkLabel(control_frame, textvariable=self.status_var, wraplength=600)
        self.status_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.launch_area = ctk.CTkScrollableFrame(self, label_text="已保存的快捷方式")
        self.launch_area.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")


        self.shortcuts = []
        
        self._load_and_display_shortcuts()

    def _log_status(self, message, is_error=False):
        prefix = "错误: " if is_error else ""
        self.status_var.set(f"{prefix}{message}")
        if is_error:
            print(f"ERROR_QuickstartPlugin: {message}")
        else:
            print(f"INFO_QuickstartPlugin: {message}")

    def _clear_launch_area(self):
        for widget in self.launch_area.winfo_children():
            widget.destroy()

    def _load_and_display_shortcuts(self):
        self._clear_launch_area()
        self.shortcuts = get_setting(TOOL_CONFIG_NAME, CONFIG_KEY_SHORTCUTS, [])
        
        if not self.shortcuts:
            self._log_status("还没有任何快捷方式。请添加一个。")
            no_items_label = ctk.CTkLabel(self.launch_area, text="没有已保存的快捷方式。")
            no_items_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            return

        self.launch_area.grid_columnconfigure(0, weight=0)
        self.launch_area.grid_columnconfigure(1, weight=1)
        self.launch_area.grid_columnconfigure(2, weight=0)
        
        for i, item in enumerate(self.shortcuts):
            name = item.get("name", "未知快捷方式")
            path = item.get("path", "") # 路径至关重要

            name_label = ctk.CTkLabel(self.launch_area, text=name, anchor="w")
            name_label.grid(row=i, column=0, padx=5, pady=5, sticky="ew")

            launch_button = ctk.CTkButton(self.launch_area, text=f"启动 {name}", command=lambda p=path, n=name: self._launch_item(p, n))
            launch_button.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            if not path or not os.path.exists(path): # 如果路径无效则禁用
                launch_button.configure(state="disabled", text=f"启动 {name} (路径无效)")


            delete_button = ctk.CTkButton(self.launch_area, text="删除", command=lambda idx=i: self._delete_shortcut_by_index(idx), width=60)
            delete_button.grid(row=i, column=2, padx=5, pady=5, sticky="e")
        
        self._log_status(f"已加载 {len(self.shortcuts)} 个快捷方式。")

    def _add_shortcut_dialog(self):
        exe_path = filedialog.askopenfilename(
            title="选择可执行文件 (.exe)",
            filetypes=(("可执行文件", "*.exe"), ("所有文件", "*.*"))
        )
        if not exe_path:
            self._log_status("添加已取消：未选择文件。")
            return

        shortcut_name_dialog = ctk.CTkInputDialog(
            text="输入此快捷方式的名称:",
            title="设置快捷方式名称"
        )
        shortcut_name = shortcut_name_dialog.get_input()

        if not shortcut_name:
            self._log_status("添加已取消：未提供名称。")
            return
            
        for s in self.shortcuts:
            if s["name"] == shortcut_name:
                messagebox.showerror("错误", f"名称 '{shortcut_name}' 已存在。")
                return
            if s["path"] == exe_path:
                messagebox.showerror("错误", f"路径 '{exe_path}' 已被快捷方式 '{s['name']}' 使用。")
                return

        self.shortcuts.append({"name": shortcut_name, "path": exe_path})
        self._save_shortcuts_and_refresh_ui()
        self._log_status(f"已添加快捷方式: {shortcut_name}")

    def _delete_shortcut_by_index(self, index):
        if 0 <= index < len(self.shortcuts):
            removed_item = self.shortcuts.pop(index)
            self._save_shortcuts_and_refresh_ui()
            self._log_status(f"已删除快捷方式: {removed_item['name']}")
        else:
            self._log_status(f"删除失败：索引 {index} 无效。", is_error=True)
            messagebox.showerror("错误", "删除快捷方式时发生内部错误 (无效索引)。")


    def _save_shortcuts_and_refresh_ui(self):
        set_setting(TOOL_CONFIG_NAME, CONFIG_KEY_SHORTCUTS, self.shortcuts)
        self._load_and_display_shortcuts() # 从配置重新加载并重绘

    def _launch_item(self, exe_path, item_name):
        self._log_status(f"正在尝试启动: {item_name} ({exe_path})")
        if not exe_path or not os.path.exists(exe_path):
            self._log_status(f"启动 '{item_name}' 失败: 路径 '{exe_path}' 无效或文件不存在。", is_error=True)
            messagebox.showerror("启动失败", f"路径 '{exe_path}' 无效或文件不存在。")
            return

        try:
            if sys.platform == "win32":
                os.startfile(exe_path)
            else:
                subprocess.Popen([exe_path])
            
            self._log_status(f"已成功发出启动 '{item_name}' 的指令。")
        except Exception as e:
            self._log_status(f"启动 '{item_name}' ({exe_path}) 失败: {e}", is_error=True)
            messagebox.showerror("启动错误", f"启动 {item_name} 时发生错误:\n{e}")