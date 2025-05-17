import customtkinter
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import scrolledtext
import os
import sys
import threading
import datetime

# 调整 sys.path 以包含项目根目录，以便导入同级模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui_app.config_manager import get_setting, set_setting

try:
    from file import folder_size_report
except ImportError:
    # 此回退适用于直接执行此文件（例如，用于测试）。
    # 在主应用程序中，上面的路径调整应该足够了。
    if os.path.basename(project_root) == 'toolbox': # 或你的项目根文件夹名称
        sys.path.insert(0, os.path.join(project_root, "..")) # 如果 project_root 是 'toolbox'，则再向上一级
        from file import folder_size_report
    else:
        raise

class ToolPluginFrame(customtkinter.CTkFrame):
    TOOL_NAME = "文件夹大小分析"
    TOOL_ORDER = 70
    CONFIG_KEY_LAST_FOLDER = "last_analyzed_folder"

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # 日志区域将扩展

        # Treeview 排序状态变量
        self._tree_sort_column = None
        self._tree_sort_reverse = False

        # --- 文件夹选择 ---
        self.folder_frame = customtkinter.CTkFrame(self)
        self.folder_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.folder_frame.grid_columnconfigure(1, weight=1)

        self.folder_label = customtkinter.CTkLabel(self.folder_frame, text="目标文件夹:")
        self.folder_label.grid(row=0, column=0, padx=(10, 5), pady=5)

        self.folder_path_var = tk.StringVar()
        last_folder = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, "")
        if last_folder and os.path.isdir(last_folder):
            self.folder_path_var.set(last_folder)

        self.folder_entry = customtkinter.CTkEntry(self.folder_frame, textvariable=self.folder_path_var, width=300)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.browse_button = customtkinter.CTkButton(self.folder_frame, text="浏览", width=80, command=self.browse_folder)
        self.browse_button.grid(row=0, column=2, padx=(0, 10), pady=5)

        # --- 控件 ---
        self.controls_frame = customtkinter.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.start_button = customtkinter.CTkButton(self.controls_frame, text="开始分析", command=self.start_analysis_thread)
        self.start_button.pack(pady=5) # 居中

        self.total_size_label_var = tk.StringVar(value="总大小: N/A")
        self.total_size_label = customtkinter.CTkLabel(self.controls_frame, textvariable=self.total_size_label_var)
        self.total_size_label.pack(pady=(0,5))

        # <<< 已添加：用于分析的进度条
        self.progress_bar = customtkinter.CTkProgressBar(self.controls_frame, orientation='horizontal', mode='indeterminate')
        # 进度条将根据需要进行 .pack() 和 .pack_forget()，因此此处不进行初始 pack。

        # --- 结果 Treeview ---
        self.tree_frame = customtkinter.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)

        columns = ("name", "size_bytes", "readable_size", "status")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("name", text="名称")
        self.tree.heading("size_bytes", text="大小 (Bytes)")
        self.tree.heading("readable_size", text="易读大小")
        self.tree.heading("status", text="状态/错误")

        self.tree.column("name", width=250, stretch=tk.YES)
        self.tree.column("size_bytes", width=100, anchor=tk.E, stretch=tk.NO)
        self.tree.column("readable_size", width=100, anchor=tk.E, stretch=tk.NO)
        self.tree.column("status", width=200, stretch=tk.YES)

        # 为每个列标题设置排序
        for col_id in columns:
            self.tree.heading(col_id, command=lambda c=col_id: self._on_treeview_sort(c))

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Treeview 的滚动条
        tree_ysb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        tree_ysb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_ysb.set)

        tree_xsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        tree_xsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=tree_xsb.set)
        
        # --- 日志区域 ---
        self.log_frame = customtkinter.CTkFrame(self)
        self.log_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, height=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state='disabled')
        self._apply_theme_to_scrolledtext(self.log_text)


    def _apply_theme_to_scrolledtext(self, st_widget):
        bg_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])
        # 配置 ScrolledText 组件本身。
        # 它会将这些配置委托给其内部的 Text 组件。
        st_widget.config(
            background=bg_color,
            foreground=text_color,
            relief="flat",      # 直接应用 relief 样式
            borderwidth=0     # 直接应用 borderwidth
        )
        # 先前导致错误的那行 st_widget.text.config(...) 已被移除。


    def _on_treeview_sort(self, column_id):
        if self._tree_sort_column == column_id:
            self._tree_sort_reverse = not self._tree_sort_reverse
        else:
            self._tree_sort_column = column_id
            self._tree_sort_reverse = False # 对于新列，默认为升序

        items_data = []
        for item_id in self.tree.get_children(''):
            # Treeview.item(item_id, 'values') 返回一个字符串元组
            item_values_tuple = self.tree.item(item_id, 'values') 
            items_data.append((item_id, item_values_tuple))

        col_index = self.tree['columns'].index(column_id)

        def sort_key_func(item_data_tuple):
            _item_id, values_tuple = item_data_tuple
            value_str = values_tuple[col_index]

            if column_id == "size_bytes":
                try:
                    return int(value_str)
                except ValueError: # 处理 "N/A" 或其他非数字字符串
                    # 如果是升序，则将非数字值排在前面；如果是降序，则排在后面
                    return float('-inf') if not self._tree_sort_reverse else float('inf') 
            elif column_id == "name" or column_id == "status" or column_id == "readable_size":
                return value_str.lower() # 不区分大小写的字符串排序
            return value_str # 其他任何意外列类型的默认排序方式

        items_data.sort(key=sort_key_func, reverse=self._tree_sort_reverse)

        # 重新排序 Treeview 中的项目
        for i, (item_id, _item_values) in enumerate(items_data):
            self.tree.move(item_id, '', i)

        # 可选：更新列标题以指示排序方向（例如使用箭头 ▲▼）
        # 为简单起见，暂时省略此功能，但以后可以通过配置添加
        # self.tree.heading(column_id, text=...) 

    def browse_folder(self):
        initial_dir = self.folder_path_var.get()
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, None)
            if not initial_dir or not os.path.isdir(initial_dir):
                 initial_dir = os.path.expanduser("~")

        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            # 清除以前的日志并记录新的文件夹选择
            self.log_message(f"选择文件夹: {folder_selected}", clear_first=True)

    def log_message(self, message, is_error=False, clear_first=False):
        self.log_text.configure(state='normal')
        if clear_first:
            self.log_text.delete(1.0, tk.END)
        
        # 如果文本区域不为空，则在新消息前确保有一个换行符
        current_content = self.log_text.get(1.0, tk.END).strip()
        if current_content: # 如果不为空则添加换行符
             self.log_text.insert(tk.END, "\n")

        # <<< 已添加：时间戳前缀
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {str(message)}"

        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def start_analysis_thread(self):
        base_path = self.folder_path_var.get()
        if not base_path or not os.path.isdir(base_path):
            self.log_message("错误: 请选择一个有效的文件夹路径。", is_error=True, clear_first=True)
            tk.messagebox.showerror("错误", "请选择一个有效的文件夹路径。")
            return

        set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, base_path)
        self.log_message(f"开始分析文件夹: {base_path}", clear_first=True)
        self.start_button.configure(state="disabled", text="分析中...")
        
        # 清除以前的结果
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.total_size_label_var.set("总大小: 计算中...")

        # <<< 已添加：显示并启动进度条
        self.progress_bar.pack(pady=(5,5), fill='x', padx=10)
        self.progress_bar.start()

        threading.Thread(target=self.perform_analysis, args=(base_path,), daemon=True).start()

    def perform_analysis(self, base_path):
        try:
            base_folder_name = os.path.basename(base_path)
            
            # 1. 获取基础文件夹本身的总大小，用于摘要标签
            total_size_bytes, logs_total, errors_total = folder_size_report.get_folder_size_recursive(
                base_path, 
                log_callback=lambda msg: self.log_message(f"[总大小计算]: {msg}")
            )

            if errors_total:
                for err in errors_total:
                    self.log_message(f"计算总大小时发生错误: {err}", is_error=True)
            
            readable_total_size = folder_size_report.human_readable_size(total_size_bytes) if total_size_bytes is not None else "N/A"
            self.total_size_label_var.set(f"总大小 ({base_folder_name}): {readable_total_size} ({total_size_bytes or 0} Bytes)")

            # 2. 获取子文件夹的统计信息
            self.log_message(f"正在获取 '{base_path}' 的子文件夹统计信息...")
            subfolders_data, summary_logs, overall_errors = folder_size_report.get_subfolder_stats(
                base_path, 
                log_callback=lambda msg: self.log_message(f"[子文件夹分析]: {msg}")
            )

            for log_entry in summary_logs:
                self.log_message(log_entry)
            for error_entry in overall_errors:
                self.log_message(f"错误: {error_entry}", is_error=True)

            if not subfolders_data and not overall_errors:
                 self.log_message("未找到子文件夹，或无法访问。")
            
            # Populate Treeview
            for item in subfolders_data:
                name, size_bytes, readable_size, status = item
                # Ensure readable_size is not None for display
                display_readable_size = readable_size if readable_size is not None else "N/A"
                display_size_bytes = size_bytes if size_bytes is not None else "N/A"
                self.tree.insert("", tk.END, values=(name, display_size_bytes, display_readable_size, status))
            
            self.log_message("分析完成。")

        except Exception as e:
            self.log_message(f"分析过程中发生严重错误: {str(e)}", is_error=True)
            self.total_size_label_var.set(f"总大小: 错误")
            import traceback
            self.log_message(traceback.format_exc(), is_error=True)
        finally:
            self.start_button.configure(state="normal", text="开始分析")
            # <<< ADDED: Stop and hide progress bar
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

if __name__ == '__main__':
    # Example usage (for testing this frame directly)
    try:
        from DUMMY_CUSTOMTKINTER_APP_FOR_TESTING import run_test_app
    except ImportError:
        # Fallback if the dummy app is not available
        # Create a simple CTk app for testing
        class SimpleTestApp(customtkinter.CTk):
            def __init__(self, tool_frame_class):
                super().__init__()
                self.title(f"Test - {tool_frame_class.TOOL_NAME}")
                self.geometry("800x700")
                
                # Ensure the theme is loaded if not already
                customtkinter.set_appearance_mode("System") # or "Dark" or "Light"
                customtkinter.set_default_color_theme("blue") # or "green" or "dark-blue"

                self.tool_frame = tool_frame_class(self)
                self.tool_frame.pack(expand=True, fill="both")

        app = SimpleTestApp(ToolPluginFrame)
        app.mainloop()
        sys.exit() # Ensure clean exit

    # If DUMMY_CUSTOMTKINTER_APP_FOR_TESTING is available:
    # This assumes you have a script like the one provided in previous interactions
    # to quickly test CTkFrames.
    # Create a dummy app structure if it doesn't exist for the test.
    if not os.path.exists("DUMMY_CUSTOMTKINTER_APP_FOR_TESTING.py"):
        with open("DUMMY_CUSTOMTKINTER_APP_FOR_TESTING.py", "w", encoding="utf-8") as f:
            f.write("""
import customtkinter
import sys

def run_test_app(tool_frame_class, tool_name="Test Tool", geometry="800x600"):
    app = customtkinter.CTk()
    app.title(tool_name)
    app.geometry(geometry)
    
    # Ensure the theme is loaded if not already
    customtkinter.set_appearance_mode("System") # or "Dark" or "Light"
    customtkinter.set_default_color_theme("blue") # or "green" or "dark-blue"
    
    frame_instance = tool_frame_class(app)
    frame_instance.pack(expand=True, fill="both")
    
    app.mainloop()
    sys.exit() # Ensure clean exit after app closes

if __name__ == '__main__':
    print("This is a dummy app for testing CTkFrames. Import run_test_app from it.")
""")
    run_test_app(ToolPluginFrame, ToolPluginFrame.TOOL_NAME, "900x750") 