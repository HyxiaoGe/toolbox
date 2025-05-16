import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import json # Needed for creating dummy config

# Adjust sys.path to include the parent directory (toolbox)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, '..')
sys.path.append(parent_dir)

from software.software_quickstart import (
    load_software_config as qs_load_config,
    launch_program as qs_launch_program,
    execute_custom_action as qs_execute_action
)

class SoftwareQuickstartFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # For the launch area

        # Configuration and status
        config_status_frame = ctk.CTkFrame(self)
        config_status_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        config_status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(config_status_frame, text="正在加载软件配置...", wraplength=self.winfo_width()-20)
        self.status_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Reload button
        self.reload_button = ctk.CTkButton(config_status_frame, text="刷新配置", command=self.load_config_and_populate_ui, width=100)
        self.reload_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        # Launch Area - Buttons will be added here dynamically
        self.launch_area = ctk.CTkScrollableFrame(self, label_text="快捷启动项")
        self.launch_area.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.launch_area.grid_columnconfigure(0, weight=1) # Ensure buttons can expand

        self.software_items = []
        self.config_file_path = os.path.join(parent_dir, "software_config.json")
        self.load_config_and_populate_ui() # Load initial config

    def _log_to_status_and_console(self, message, is_error=False):
        prefix = "错误: " if is_error else "状态: "
        full_message = f"{prefix}{message}"
        self.status_label.configure(text=full_message)
        # print(full_message) # Optional: for console debugging during development
        if is_error:
            print(f"ERROR_QuickstartFrame: {message}")
        else:
            print(f"INFO_QuickstartFrame: {message}")


    def load_config_and_populate_ui(self):
        # Clear existing buttons in launch area
        for widget in self.launch_area.winfo_children():
            widget.destroy()
        self.software_items = []
        self._log_to_status_and_console("正在从配置文件加载启动项...")

        config_data, message = qs_load_config(self.config_file_path)

        if config_data and "software" in config_data:
            self.software_items = config_data.get("software", [])
            self._log_to_status_and_console(f"配置已加载: {len(self.software_items)} 项。")
            if not self.software_items:
                 self._log_to_status_and_console("配置文件中未找到 'software' 项目或列表为空。", is_error=True)
                 no_items_label = ctk.CTkLabel(self.launch_area, text="配置文件中没有有效的快捷启动项。")
                 no_items_label.grid(row=0, column=0, padx=10, pady=10)
                 return
        elif not os.path.exists(self.config_file_path):
            self._log_to_status_and_console(f"配置文件 '{os.path.basename(self.config_file_path)}' 未找到。将创建示例配置。", is_error=True)
            # Create a dummy config if not found for demonstration
            dummy_config = {
                "software": [
                    {"name": "记事本 (示例)", "path": "notepad.exe", "args": []},
                    {"name": "计算器 (示例)", "path": "calc.exe"},
                    {
                        "name": "打开测试文档 (示例)", 
                        "action": "open_default", 
                        "target_file": os.path.join(parent_dir, "dummy_document_for_quickstart.txt") 
                    }
                ]
            }
            try:
                with open(self.config_file_path, 'w', encoding='utf-8') as f:
                    json.dump(dummy_config, f, indent=4)
                # Create dummy document for the example action
                dummy_doc_path = os.path.join(parent_dir, "dummy_document_for_quickstart.txt")
                if not os.path.exists(dummy_doc_path):
                    with open(dummy_doc_path, 'w', encoding='utf-8') as df:
                        df.write("这是一个通过软件快捷启动模块的 'open_default' 动作打开的示例文档。")
                self._log_to_status_and_console(f"已创建示例配置文件和文档。请按需修改后点击'刷新配置'。")
                self.software_items = dummy_config["software"] # Use dummy items for now
            except Exception as e_create:
                self._log_to_status_and_console(f"创建示例配置文件失败: {e_create}", is_error=True)
                messagebox.showerror("配置错误", f"创建示例 software_config.json 失败: {e_create}")
                return # Stop if dummy creation fails
        else: # Config file exists but error during load (e.g. JSON malformed)
            self._log_to_status_and_console(f"加载配置文件失败: {message}", is_error=True)
            messagebox.showerror("配置加载错误", f"加载 {os.path.basename(self.config_file_path)} 失败: {message}")
            no_items_label = ctk.CTkLabel(self.launch_area, text=f"加载配置失败。请检查文件: {os.path.basename(self.config_file_path)}")
            no_items_label.grid(row=0, column=0, padx=10, pady=10)
            return

        # Create buttons for each software item
        for i, item in enumerate(self.software_items):
            btn_text = item.get("name", f"项目 {i+1}")
            # Create a new function scope for lambda to capture current item
            def create_lambda(current_item):
                return lambda: self.launch_software_item(current_item)
            
            button = ctk.CTkButton(self.launch_area, text=btn_text, command=create_lambda(item))
            button.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
        
        if not self.software_items and os.path.exists(self.config_file_path):
            # This case implies the file exists but is empty or has no software list
            self._log_to_status_and_console("配置文件已加载，但未找到有效的软件项。", is_error=True)
            no_items_label = ctk.CTkLabel(self.launch_area, text="配置文件中没有有效的快捷启动项。")
            no_items_label.grid(row=0, column=0, padx=10, pady=10)

    def launch_software_item(self, software_item):
        item_name = software_item.get("name", "未知项")
        self._log_to_status_and_console(f"准备启动: {item_name}...")

        success = False
        message = "配置项无效"

        if "path" in software_item:
            exe_path = software_item["path"]
            args = software_item.get("args", [])
            # Ensure path is absolute or discoverable if relative
            # For simplicity, current qs_launch_program expects an existing path
            # Advanced: could try to resolve relative to project root or system PATH
            success, message = qs_launch_program(exe_path, args)
        
        elif "action" in software_item:
            # Pass the GUI logger to the action executor
            success, message = qs_execute_action(software_item, log_callback_gui=self._log_to_status_and_console)
        else:
            message = f"'{item_name}' 的配置无效 (缺少 'path' 或 'action' 键)。"
            self._log_to_status_and_console(message, is_error=True)
            messagebox.showerror("配置错误", message)
            return

        if success:
            self._log_to_status_and_console(f"'{item_name}': {message}")
            # messagebox.showinfo("操作提示", f"'{item_name}': 操作已尝试执行。\n{message}") # Can be too noisy
        else:
            self._log_to_status_and_console(f"'{item_name}' 执行失败: {message}", is_error=True)
            messagebox.showerror("执行失败", f"'{item_name}' 执行失败: {message}")

if __name__ == '__main__':
    # This is for testing the frame independently
    root = ctk.CTk()
    root.title("Test Software Quickstart Frame")
    root.geometry("500x600")
    # Ensure a dummy config exists for testing, or the frame will try to create it.
    # For isolated testing, good to manage this outside the frame logic if possible.
    # Example: Create a config in the parent of where this script would run from in test.
    # (e.g., if script is in gui_app, create software_config.json in its parent folder)
    
    test_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "software_config.json")
    print(f"Test mode: expecting software_config.json at: {test_config_path}")
    # if not os.path.exists(test_config_path): # Optionally create a very basic one for test
    #     print(f"Creating a minimal {test_config_path} for testing frame.")
    #     with open(test_config_path, 'w', encoding='utf-8') as f:
    #         json.dump({"software": [{"name": "Test Notepad", "path": "notepad.exe"}]}, f, indent=4)

    frame = SoftwareQuickstartFrame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    root.mainloop() 