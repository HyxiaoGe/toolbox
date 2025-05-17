import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import os
import sys
import datetime # <<< 已添加：用于时间戳

# 调整 sys.path 以包含项目根目录，以便导入后端模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file.file_find_duplicates import collect_duplicate_files_info, move_files_to_duplicate_folder
from gui_app.config_manager import get_setting, set_setting

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "查找重复文件"
    TOOL_ORDER = 50
    CONFIG_KEY_LAST_FOLDER = "last_scan_folder"
    CONFIG_KEY_DUPLICATES_SUBDIR = "duplicates_subdir_name"
    DEFAULT_DUPLICATES_SUBDIR = "duplicates_found"

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 允许结果/日志框架扩展

        # <<< 已添加：Treeview 排序状态变量
        self._tree_sort_column = None
        self._tree_sort_reverse = False

        self.folder_path_var = tk.StringVar()
        self.found_duplicate_groups = {}
        self.selected_folder_for_scan = ""

        # --- UI 元素 ---
        # 文件夹选择
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="目标文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_frame, textvariable=self.folder_path_var)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ctk.CTkButton(folder_frame, text="浏览", width=70, command=self.browse_folder)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        # 操作按钮
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        self.find_button = ctk.CTkButton(action_frame, text="1. 查找重复文件", command=self.find_duplicates_action)
        self.find_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.move_button = ctk.CTkButton(action_frame, text="2. 移动找到的重复项", command=self.move_duplicates_action, state=tk.DISABLED)
        self.move_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 结果 Treeview
        results_frame = ctk.CTkFrame(self)
        results_frame.grid(row=2, column=0, padx=10, pady=(0,5), sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(results_frame, columns=("hash", "count", "files"), show='headings', height=10)
        self.tree.heading("hash", text="哈希 (部分)")
        self.tree.heading("count", text="数量")
        self.tree.heading("files", text="文件列表 (部分)")
        self.tree.column("hash", width=120, stretch=tk.NO)
        self.tree.column("count", width=60, stretch=tk.NO, anchor='center')
        self.tree.column("files", width=450) # 为文件列表提供更多空间

        # <<< 已添加：为每个列标题设置排序
        for col_id in self.tree["columns"]:
            self.tree.heading(col_id, command=lambda c=col_id: self._on_treeview_sort(c))

        self.tree.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        tree_scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar_y.set)
        tree_scrollbar_y.grid(row=0, column=1, sticky="ns")
        tree_scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_scrollbar_x.set)
        tree_scrollbar_x.grid(row=1, column=0, sticky="ew")

        # 日志显示区域
        log_label = ctk.CTkLabel(self, text="日志:")
        log_label.grid(row=3, column=0, padx=10, pady=(5,0), sticky="w")
        self.log_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=6, undo=True)
        self.log_text_area.grid(row=4, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.grid_rowconfigure(4, weight=0) # 日志区域具有固定的初始高度，结果区域可扩展
        self._apply_theme_to_scrolledtext(self.log_text_area)

        self.log_message("请选择要扫描重复文件的文件夹。", clear_log=True)
        self.log_message("注意: 移动操作会将文件整理到所选扫描文件夹下的 'duplicates_found' 子目录中。")

        # 从配置加载上次使用的文件夹
        last_folder = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, "")
        if last_folder and os.path.isdir(last_folder): # 检查路径是否仍然有效
            self.folder_path_var.set(last_folder)
            self.selected_folder_for_scan = last_folder
            self.log_message(f"已加载上次使用的文件夹: {last_folder}", clear_log=True)

    # <<< 已添加：处理 Treeview 列排序的方法
    def _on_treeview_sort(self, column_id):
        if self._tree_sort_column == column_id:
            self._tree_sort_reverse = not self._tree_sort_reverse
        else:
            self._tree_sort_column = column_id
            self._tree_sort_reverse = False # 对于新列，默认为升序

        items_data = []
        for item_id in self.tree.get_children(''):
            item_values_tuple = self.tree.item(item_id, 'values') 
            items_data.append((item_id, item_values_tuple))

        col_index = self.tree['columns'].index(column_id)

        def sort_key_func(item_data_tuple):
            _item_id, values_tuple = item_data_tuple
            value_str = values_tuple[col_index]

            if column_id == "count":
                try:
                    return int(value_str)
                except ValueError:
                    return float('-inf') if not self._tree_sort_reverse else float('inf') 
            elif column_id == "hash" or column_id == "files":
                return value_str.lower() # 不区分大小写的字符串排序
            return value_str 

        items_data.sort(key=sort_key_func, reverse=self._tree_sort_reverse)

        for i, (item_id, _item_values) in enumerate(items_data):
            self.tree.move(item_id, '', i)
        # 可选：更新列标题文本以显示排序指示符 (▲/▼)

    def _apply_theme_to_scrolledtext(self, text_widget):
        try:
            is_dark = ctk.get_appearance_mode().lower() == "dark"
            bg_color = ctk.ThemeManager.theme["CTkTextbox"]["fg_color"]
            text_color = ctk.ThemeManager.theme["CTkTextbox"]["text_color"]
            border_color = ctk.ThemeManager.theme["CTkTextbox"]["border_color"]
            border_width = ctk.ThemeManager.theme["CTkTextbox"]["border_width"]

            current_bg = bg_color[1] if isinstance(bg_color, (list, tuple)) and is_dark else bg_color[0] if isinstance(bg_color, (list, tuple)) else bg_color
            current_text = text_color[1] if isinstance(text_color, (list, tuple)) and is_dark else text_color[0] if isinstance(text_color, (list, tuple)) else text_color
            current_border = border_color[1] if isinstance(border_color, (list, tuple)) and is_dark else border_color[0] if isinstance(border_color, (list, tuple)) else border_color
            
            text_widget.config(
                background=current_bg,
                foreground=current_text,
                insertbackground=current_text, 
                font=("Segoe UI", ctk.ThemeManager.theme["CTkFont"]["size"]) if "CTkFont" in ctk.ThemeManager.theme else ("Arial", 12),
                relief=tk.FLAT, 
                borderwidth=border_width,
                highlightbackground=current_border,
                highlightcolor=current_border,
                highlightthickness=border_width,
                padx=5, pady=5,
                state=tk.DISABLED
            )
        except Exception:
            text_widget.config(font=("Arial", 11), relief=tk.SOLID, borderwidth=1, state=tk.DISABLED)
            pass

    def log_message(self, message, is_error=False, clear_log=False):
        self.log_text_area.configure(state=tk.NORMAL)
        if clear_log:
            self.log_text_area.delete("1.0", tk.END)
        
        prefix = "[错误] " if is_error else ""
        if not message.endswith("\n"):
            message += "\n"
        
        # <<< 已添加：时间戳前缀
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 如果存在前缀，请确保它在时间戳之前，作为核心消息的一部分
        # 并确保最终消息有换行符。
        formatted_message = f"[{timestamp}] {prefix}{message.rstrip()}" + "\n"

        self.log_text_area.insert(tk.END, formatted_message) # <<< 已修改：使用 formatted_message
        self.log_text_area.see(tk.END)
        self.log_text_area.configure(state=tk.DISABLED)

    def browse_folder(self):
        # 根据当前条目或上次保存的路径建议初始目录
        initial_dir = self.folder_path_var.get() 
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, None)
            if not initial_dir or not os.path.isdir(initial_dir): # 如果保存的路径也无效，则使用回退路径
                 initial_dir = os.path.expanduser("~") # 如果没有其他路径，则默认为用户主目录

        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.selected_folder_for_scan = folder_selected # 存储以供移动操作使用
            self.log_message(f"已选择文件夹: {folder_selected}", clear_log=True)
            self.clear_results()
            self.move_button.configure(state=tk.DISABLED)
            # 此处暂不保存，在成功扫描操作后再保存

    def clear_results(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.found_duplicate_groups = {}

    def find_duplicates_action(self):
        folder_to_scan = self.folder_path_var.get()
        if not folder_to_scan or not os.path.isdir(folder_to_scan):
            messagebox.showerror("错误", "请选择一个有效的文件夹进行扫描。")
            return

        self.selected_folder_for_scan = folder_to_scan
        self.log_message(f"开始在 {folder_to_scan} 中查找重复文件...", clear_log=True)
        self.clear_results()
        self.find_button.configure(state=tk.DISABLED, text="正在查找...")
        self.move_button.configure(state=tk.DISABLED)
        self.update_idletasks()

        try:
            duplicate_groups, logs, processed, unsupp, err_hash = collect_duplicate_files_info(folder_to_scan)
            
            for log_entry in logs:
                self.log_message(log_entry)
            
            self.found_duplicate_groups = duplicate_groups

            if not duplicate_groups:
                self.log_message("扫描完成。未找到任何重复文件组。") # 来自后端的 log_messages 已包含摘要
            else:
                # 关于找到的组的日志消息已经是后端 'logs' 的一部分
                for i, (hash_val, paths) in enumerate(duplicate_groups.items()):
                    files_display_list = [os.path.basename(p) for p in paths]
                    # 限制在树状视图中显示的文件数量，以便预览
                    max_files_in_tree_item = 3
                    files_str = ", ".join(files_display_list[:max_files_in_tree_item])
                    if len(files_display_list) > max_files_in_tree_item:
                        files_str += f", ... ({len(files_display_list) - max_files_in_tree_item} more)"
                    
                    self.tree.insert("", tk.END, iid=str(i), values=(hash_val[:12] + "...", len(paths), files_str))
                    # self.tree.item(str(i), tags=(hash_val,)) # 存储完整哈希值可能以后有用
                self.move_button.configure(state=tk.NORMAL)
                
                # 将成功扫描的文件夹保存到配置
                set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, folder_to_scan)
                self.log_message(f"当前扫描文件夹 '{folder_to_scan}' 已记录以备下次使用。")

        except Exception as e:
            self.log_message(f"查找重复文件时发生意外错误: {e}", is_error=True)
            messagebox.showerror("查找失败", f"发生意外错误: {e}")
        finally:
            self.find_button.configure(state=tk.NORMAL, text="1. 查找重复文件")

    def move_duplicates_action(self):
        if not self.found_duplicate_groups or not self.selected_folder_for_scan:
            messagebox.showwarning("无操作", "没有找到可移动的重复文件，或者未指定扫描文件夹。")
            return

        # （在 move_duplicates_action 中，如果已实现）
        # 这将是 self.selected_folder_for_scan 内的子文件夹
        # 例如 "duplicates_found"
        duplicates_subfolder_name = get_setting(ToolPluginFrame.TOOL_NAME, 
                                                ToolPluginFrame.CONFIG_KEY_DUPLICATES_SUBDIR, 
                                                ToolPluginFrame.DEFAULT_DUPLICATES_SUBDIR)
        
        target_duplicate_dir = os.path.join(self.selected_folder_for_scan, duplicates_subfolder_name)

        confirm_move = messagebox.askyesno("确认移动", 
            f"确定要将找到的重复文件（每组保留一个）移动到以下子文件夹吗？\n\n{target_duplicate_dir}\n\n如果子文件夹不存在，将会自动创建。此操作不可轻易撤销。",
            icon=messagebox.WARNING)

        if not confirm_move:
            self.log_message("移动操作已取消。")
            return

        self.log_message(f"开始移动重复文件到 {target_duplicate_dir} ...")
        self.move_button.configure(state=tk.DISABLED, text="正在移动...")
        self.find_button.configure(state=tk.DISABLED) # Also disable find during move
        self.update_idletasks()
        
        moved_count_total = 0
        error_count_total = 0
        groups_processed = 0

        # 遍历项目的副本，因为如果组内某些移动部分失败，我们可能会修改字典
        for hash_val, paths in list(self.found_duplicate_groups.items()): # Iterate over a copy
            if len(paths) > 1:
                # 每个重复组只保留第一个文件，移动其余文件
                files_to_move = paths[1:] 
                moved_files, error_files = move_files_to_duplicate_folder(files_to_move, target_duplicate_dir, self.selected_folder_for_scan)
                
                moved_count_total += len(moved_files)
                error_count_total += len(error_files)
                groups_processed += 1

                for f_path in moved_files:
                    self.log_message(f"已移动: {f_path}")
                for f_path, err_msg in error_files:
                    self.log_message(f"移动失败: {f_path} - {err_msg}", is_error=True)
            
        self.log_message(f"移动操作完成。总共移动 {moved_count_total} 个文件，处理 {groups_processed} 个重复组，发生 {error_count_total} 个错误。")
        messagebox.showinfo("移动完成", f"成功移动 {moved_count_total} 个重复文件。\n发生 {error_count_total} 个错误。\n详情请查看日志。")
        
        # 移动文件并更新日志/UI
        # 如果需要，刷新树状视图，或者在通过移动"解决"重复项后清除它
        self.clear_results() # Clear tree and internal list as they are now outdated
        self.find_button.configure(state=tk.NORMAL, text="1. 查找重复文件")
        # Keep move button disabled as there are no results to move now

if __name__ == '__main__':
    # 示例用法（用于直接测试此框架）
    try:
        from DUMMY_CUSTOMTKINTER_APP_FOR_TESTING import run_test_app
    except ImportError:
        # 如果虚拟应用程序不可用，则使用回退
        # 创建一个简单的 CTk 应用以进行测试
        class SimpleTestApp(customtkinter.CTk):
            def __init__(self, tool_frame_class):
                super().__init__()
                self.title(f"Test - {tool_frame_class.TOOL_NAME}")
                self.geometry("800x700")
                
                # 确保主题已加载（如果尚未加载）
                customtkinter.set_appearance_mode("System") # 或 "Dark" 或 "Light"
                customtkinter.set_default_color_theme("blue") # 或 "green" 或 "dark-blue"

                self.tool_frame = tool_frame_class(self)
                self.tool_frame.pack(expand=True, fill="both")

        app = SimpleTestApp(ToolPluginFrame)
        app.mainloop()
        sys.exit() # 确保干净退出

    # 如果 DUMMY_CUSTOMTKINTER_APP_FOR_TESTING 可用：
    # 此处假设你拥有先前交互中提供的那种脚本
    # 用于快速测试 CTkFrames。
    # 如果测试用的虚拟应用结构不存在，则创建它。
    if not os.path.exists("DUMMY_CUSTOMTKINTER_APP_FOR_TESTING.py"):
        with open("DUMMY_CUSTOMTKINTER_APP_FOR_TESTING.py", "w", encoding="utf-8") as f:
            f.write("""
import customtkinter
import sys

def run_test_app(tool_frame_class, tool_name="Test Tool", geometry="800x600"):
    app = customtkinter.CTk()
    app.title(tool_name)
    app.geometry(geometry)
    
    # 确保主题已加载（如果尚未加载）
    customtkinter.set_appearance_mode("System") # 或 "Dark" 或 "Light"
    customtkinter.set_default_color_theme("blue") # 或 "green" 或 "dark-blue"
    
    frame_instance = tool_frame_class(app)
    frame_instance.pack(expand=True, fill="both")
    
    app.mainloop()
    sys.exit() # 确保应用关闭后干净退出

if __name__ == '__main__':
    print("This is a dummy app for testing CTkFrames. Import run_test_app from it.")
""")
    run_test_app(ToolPluginFrame, ToolPluginFrame.TOOL_NAME, "900x750") 