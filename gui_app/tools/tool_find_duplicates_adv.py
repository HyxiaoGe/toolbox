import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import os
import sys
import datetime
import threading
from collections import defaultdict
from file.file_find_duplicates_enhanced import collect_duplicate_files_info_enhanced, EnhancedDuplicateFinder, DuplicateGroup, FileMetadata, DuplicateLevel
from file.file_find_duplicates import move_files_to_duplicate_folder
import logging
from typing import Dict, List
import re

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui_app.config_manager import get_setting, set_setting

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "高级重复文件查找"
    TOOL_DESCRIPTION = "在指定文件夹中查找重复的文件，并可以选择移动它们。"
    TOOL_ORDER = 50
    CONFIG_KEY_LAST_FOLDER = "last_scan_folder"
    CONFIG_KEY_DUPLICATES_SUBDIR = "duplicates_subdir_name"
    DEFAULT_DUPLICATES_SUBDIR = "duplicates_found"
    CONFIG_KEY_LAST_FFPROBE_PATH = "last_ffprobe_path"

    def __init__(self, master):
        super().__init__(master)
        # Configure a 3-column layout for the main frame
        self.grid_columnconfigure(0, weight=1)  # Left spacer column
        self.grid_columnconfigure(1, weight=0)  # Middle column for non-expanding content
        self.grid_columnconfigure(2, weight=1)  # Right spacer column
        
        # Row configuration for vertical expansion where needed (e.g., results_frame)
        self.grid_rowconfigure(3, weight=1) # results_frame row
        # Other rows can have weight 0 by default or explicitly set if needed
        # self.grid_rowconfigure(5, weight=0) # details_text_area (compact height)
        # self.grid_rowconfigure(7, weight=0) # log_text_area (compact height)

        self._tree_sort_column = None
        self._tree_sort_reverse = False

        self.folder_path_var = tk.StringVar()
        self.found_duplicate_groups = {}
        self.selected_folder_for_scan = ""
        self.ffprobe_path_var = tk.StringVar()
        self.scan_stop_event = None
        self.current_scan_thread = None

        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1) # Inner column of folder_frame expands

        ctk.CTkLabel(folder_frame, text="目标文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_frame, textvariable=self.folder_path_var)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ctk.CTkButton(folder_frame, text="浏览", width=70, command=self.browse_folder)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        ffprobe_frame = ctk.CTkFrame(self)
        ffprobe_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0,10), sticky="ew")
        ffprobe_frame.grid_columnconfigure(0, weight=0) # 标签列，不扩展
        ffprobe_frame.grid_columnconfigure(1, weight=1) # 输入框列，扩展
        ffprobe_frame.grid_columnconfigure(2, weight=0) # 浏览按钮列，不扩展

        ctk.CTkLabel(ffprobe_frame, text="ffprobe路径:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ffprobe_path_entry = ctk.CTkEntry(ffprobe_frame, textvariable=self.ffprobe_path_var, width=300, placeholder_text="可选，例如 D:\\ffmpeg\\bin\\ffprobe.exe")
        self.ffprobe_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(ffprobe_frame, text="浏览", command=self.browse_ffprobe_path).grid(row=0, column=2, padx=5, pady=5)

        # Create a container for the action_frame to control its centering and prevent expansion
        action_frame_container = ctk.CTkFrame(self)
        # Place action_frame_container in the middle (column 1) of the ToolPluginFrame
        action_frame_container.grid(row=2, column=1, padx=10, pady=(0,10), sticky="n") 
        # No need for columnconfigure on action_frame_container if action_frame is its only centered child

        # action_frame is now placed inside action_frame_container
        action_frame = ctk.CTkFrame(action_frame_container) 
        action_frame.grid(row=0, column=0, sticky="") # action_frame itself does not stick or expand within its container
        action_frame.grid_columnconfigure(0, weight=0)
        action_frame.grid_columnconfigure(1, weight=0)
        action_frame.grid_columnconfigure(2, weight=0)

        self.find_button = ctk.CTkButton(action_frame, text="1. 查找重复文件", command=self.start_find_duplicates_thread)
        self.find_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.move_button = ctk.CTkButton(action_frame, text="2. 移动找到的重复项", command=self.move_duplicates_action, state=tk.DISABLED)
        self.move_button.grid(row=0, column=1, padx=5, pady=5)

        self.stop_button = ctk.CTkButton(action_frame, text="终止扫描", command=self.stop_scan_action, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=5, pady=5)

        results_frame = ctk.CTkFrame(self)
        results_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(0,5), sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # 新的列定义
        self.tree_columns = ("item_name", "item_path", "item_size", "item_duration", "group_info")
        self.tree_column_headings = {
            "item_name": "文件名",
            "item_path": "文件路径",
            "item_size": "大小",
            "item_duration": "时长",
            "group_info": "重复信息" # (等级/评分/原因)
        }
        self.tree_column_widths = {
            "item_name": 200,
            "item_path": 300,
            "item_size": 100,
            "item_duration": 80,
            "group_info": 150
        }
        self.tree_column_anchors = {
            "item_name": "w",
            "item_path": "w",
            "item_size": "e",
            "item_duration": "e",
            "group_info": "w"
        }

        self.tree = ttk.Treeview(results_frame, columns=self.tree_columns, show='headings', height=10)
        
        for col_id in self.tree_columns:
            self.tree.heading(col_id, text=self.tree_column_headings[col_id], command=lambda c=col_id: self._on_treeview_sort(c))
            self.tree.column(col_id, width=self.tree_column_widths[col_id], anchor=self.tree_column_anchors[col_id], stretch=True) # stretch=True for resizable by default

        self.tree.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_treeview_select) # 绑定选择事件

        tree_scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar_y.set)
        tree_scrollbar_y.grid(row=0, column=1, sticky="ns")
        tree_scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_scrollbar_x.set)
        tree_scrollbar_x.grid(row=1, column=0, sticky="ew")

        # 新增：选中项详细路径显示区域
        details_label = ctk.CTkLabel(self, text="选中组的详细路径:")
        details_label.grid(row=4, column=0, columnspan=3, padx=10, pady=(5,0), sticky="w")
        self.details_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=4, undo=True)
        self.details_text_area.grid(row=5, column=0, columnspan=3, padx=10, pady=(0,5), sticky="nsew")
        # self.grid_rowconfigure(5, weight=0) # Already default or managed by content height
        self._apply_theme_to_scrolledtext(self.details_text_area)
        self.details_text_area.configure(state=tk.DISABLED)

        log_label = ctk.CTkLabel(self, text="日志:")
        log_label.grid(row=6, column=0, columnspan=3, padx=10, pady=(5,0), sticky="w")
        self.log_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=6, undo=True)
        self.log_text_area.grid(row=7, column=0, columnspan=3, padx=10, pady=(0,10), sticky="nsew")
        # self.grid_rowconfigure(7, weight=0) # Already default
        self._apply_theme_to_scrolledtext(self.log_text_area)

        self.status_label = ctk.CTkLabel(self, text="准备就绪", wraplength=480)
        self.status_label.grid(row=8, column=0, columnspan=3, padx=10, pady=(5,0), sticky="w")

        self.log_message("请选择要扫描重复文件的文件夹。", clear_log=True)
        self.log_message("注意: 移动操作会将文件整理到所选扫描文件夹下的 'duplicates_found' 子目录中。")

        last_folder = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, "")
        if last_folder and os.path.isdir(last_folder):
            self.folder_path_var.set(last_folder)
            self.selected_folder_for_scan = last_folder
            self.log_message(f"已加载上次使用的文件夹: {last_folder}", clear_log=True)
        
        # 加载上次使用的 ffprobe 路径
        last_ffprobe = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FFPROBE_PATH, "")
        if last_ffprobe and os.path.isfile(last_ffprobe):
            self.ffprobe_path_var.set(last_ffprobe)
            self.log_message(f"已加载上次使用的ffprobe路径: {last_ffprobe}", "INFO")

    def _sort_str_as_num(self, s: str, reverse=False):
        """Helper for sorting strings that might represent numbers, handling non-numeric gracefully."""
        try:
            # Extract numeric part, e.g., from "123 MB" or "10.5s"
            num_part = re.match(r'[\d\.]+', s)
            if num_part:
                return float(num_part.group(0))
        except (ValueError, TypeError):
            pass
        # Fallback for non-numeric or unparsable strings
        return float('-inf') if not reverse else float('inf') # Sort non-numeric to one end

    def _on_treeview_sort(self, column_id):
        if not self.found_duplicate_groups or not isinstance(self.found_duplicate_groups, list):
            return # No data to sort

        if self._tree_sort_column == column_id:
            self._tree_sort_reverse = not self._tree_sort_reverse
        else:
            self._tree_sort_column = column_id
            self._tree_sort_reverse = False

        # Get the actual list of DuplicateGroup objects
        data_to_sort: List[DuplicateGroup] = self.found_duplicate_groups

        def sort_key_func(group: DuplicateGroup):
            if column_id == "item_name": # "文件名" (组级别是 等级(数量) )
                return (group.level.value, len(group.files))
            elif column_id == "item_path": # "文件路径" (组级别为空) -> no specific sort for group
                return "" # Or perhaps sort by first file's path, but might be slow
            elif column_id == "item_size": # "大小" (组级别为空)
                if group.files:
                    # Attempt to parse size from the first file's metadata for sorting group
                    # This is a heuristic. A proper numeric sort would require storing raw bytes.
                    return group.files[0].size if group.files[0].size is not None else (float('-inf') if not self._tree_sort_reverse else float('inf'))
                return float('-inf') if not self._tree_sort_reverse else float('inf')
            elif column_id == "item_duration": # "时长" (组级别为空)
                if group.files and group.files[0].duration is not None:
                    return group.files[0].duration
                return float('-inf') if not self._tree_sort_reverse else float('inf')
            elif column_id == "group_info": # "重复信息" (组级别是 评分 | 原因)
                return group.score
            return "" # Default fallback

        try:
            data_to_sort.sort(key=sort_key_func, reverse=self._tree_sort_reverse)
        except Exception as e_sort:
            self.log_message(f"排序时发生错误: {e_sort}", "ERROR")
            return
        
        # Repopulate the treeview with the sorted data
        self.populate_treeview_from_results()

    def _apply_theme_to_scrolledtext(self, text_widget):
        try:
            is_dark = ctk.get_appearance_mode().lower() == "dark"
            # 确保使用正确的主题键
            textbox_theme = ctk.ThemeManager.theme.get("CTkTextbox", ctk.ThemeManager.theme.get("CTkEntry", {})) 
            
            bg_color = textbox_theme.get("fg_color")
            text_color = textbox_theme.get("text_color")
            border_color = textbox_theme.get("border_color", textbox_theme.get("fg_color")) # 兼容旧版
            border_width = textbox_theme.get("border_width", 0)

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
        except Exception as e:
            # Fallback if theme keys are missing or incorrect
            logging.warning(f"Error applying theme to ScrolledText: {e}")
            text_widget.config(font=("Arial", 11), relief=tk.SOLID, borderwidth=1, state=tk.DISABLED)
            pass

    def log_message(self, message, level="INFO", clear_log=False):
        if not isinstance(message, str):
            message = str(message)
            
        self.log_text_area.configure(state=tk.NORMAL)
        if clear_log:
            self.log_text_area.delete("1.0", tk.END)
        
        prefix = f"[{level.upper()}] " if level.upper() != "INFO" else ""
        if not message.endswith("\n"):
            message += "\n"
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        formatted_message = f"[{timestamp}] {prefix}{message.rstrip()}" + "\n"

        self.log_text_area.insert(tk.END, formatted_message)
        self.log_text_area.see(tk.END)
        self.log_text_area.update_idletasks() # 强制更新UI以显示实时日志
        self.log_text_area.configure(state=tk.DISABLED)

    def browse_folder(self):
        initial_dir = self.folder_path_var.get() 
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, None)
            if not initial_dir or not os.path.isdir(initial_dir):
                initial_dir = os.path.expanduser("~")

        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.selected_folder_for_scan = folder_selected
            self.log_message(f"已选择文件夹: {folder_selected}", clear_log=True)
            self.clear_results()
            self.move_button.configure(state=tk.DISABLED)

    def browse_ffprobe_path(self):
        initial_dir = self.ffprobe_path_var.get()
        if not initial_dir or not os.path.isfile(initial_dir):
            initial_dir = os.path.expanduser("~")

        file_selected = filedialog.askopenfilename(initialdir=initial_dir, filetypes=[("ffprobe executable", "*.exe")])
        if file_selected:
            self.ffprobe_path_var.set(file_selected)
            self.log_message(f"已选择ffprobe路径: {file_selected}", clear_log=True)

    def clear_results(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def start_find_duplicates_thread(self):
        folder_to_scan = self.folder_path_var.get()
        if not folder_to_scan or not os.path.isdir(folder_to_scan):
            messagebox.showerror("错误", "请选择一个有效的文件夹进行扫描。")
            return
        
        if self.current_scan_thread and self.current_scan_thread.is_alive():
            messagebox.showinfo("提示", "一个扫描任务已经在运行中。")
            return

        self.selected_folder_for_scan = folder_to_scan
        self.log_message(f"开始在 {folder_to_scan} 中查找重复文件...", clear_log=True)
        self.clear_results()
        self.find_button.configure(state=tk.DISABLED, text="正在查找...")
        self.move_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.update_idletasks()

        self.found_duplicate_groups = {}
        self.scan_stop_event = threading.Event()
        self.current_scan_thread = threading.Thread(target=self.find_duplicates_action_threaded, daemon=True)
        self.current_scan_thread.start()

    def find_duplicates_action_threaded(self):
        folder_to_scan = self.selected_folder_for_scan
        ffprobe_path = self.ffprobe_path_var.get()
        finder = None 

        try:
            finder = EnhancedDuplicateFinder(
                ffprobe_path=(ffprobe_path if ffprobe_path and os.path.isfile(ffprobe_path) else None),
                log_callback=lambda msg, lvl: self.master.after(0, self.log_message, msg, lvl), 
                stop_event=self.scan_stop_event
            )

            current_ffprobe_in_use = finder.ffprobe_path 
            
            if current_ffprobe_in_use and os.path.isfile(current_ffprobe_in_use):
                # 如果ffprobe路径有效（无论是用户提供还是自动检测到的），则保存它
                if self.ffprobe_path_var.get() != current_ffprobe_in_use: # 如果是自动检测更新的
                     self.master.after(0, lambda: self.ffprobe_path_var.set(current_ffprobe_in_use))
                     self.master.after(0, self.log_message, f"自动找到ffprobe并更新路径: {current_ffprobe_in_use}", "INFO")
                
                set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FFPROBE_PATH, current_ffprobe_in_use)
                # self.master.after(0, self.log_message, f"ffprobe路径已缓存: {current_ffprobe_in_use}", "DEBUG") # 可以移除或保留DEBUG日志

            elif not current_ffprobe_in_use and (not ffprobe_path or not os.path.isfile(ffprobe_path)):
                self.master.after(0, self.log_message, "ffprobe路径未提供且自动检测失败，视频时长将不可用。", "WARNING")
            
            self.master.after(0, self.log_message, f"线程开始在文件夹 '{folder_to_scan}' 中查找重复文件 (使用核心查找器)...", "INFO")
            
            # 直接调用核心方法，它返回 Dict[DuplicateLevel, List[DuplicateGroup]]
            raw_results: Dict[DuplicateLevel, List[DuplicateGroup]] = finder.find_duplicates_in_directory(folder_to_scan)
            
            # 转换为扁平化的 List[DuplicateGroup] 并按分数排序
            processed_results: List[DuplicateGroup] = []
            for level_key in sorted(raw_results.keys(), key=lambda x: x.value): 
                processed_results.extend(raw_results[level_key])
            
            # 按组的最高分数降序排序，确保分数高的组显示在前面
            processed_results.sort(key=lambda g: g.score, reverse=True)
            
            self.found_duplicate_groups = processed_results # 存储这个丰富的结果
            
            log_msg_level = "INFO"
            if self.scan_stop_event and self.scan_stop_event.is_set():
                log_msg = "扫描已被用户中止。"
                log_msg_level = "WARNING"
            elif not self.found_duplicate_groups:
                log_msg = "扫描完成。未找到任何符合当前设置的重复文件组。"
            else:
                log_msg = f"扫描完成。找到 {len(self.found_duplicate_groups)} 个重复文件组。"
            
            self.master.after(0, self.log_message, log_msg, log_msg_level)
            
            if not (self.scan_stop_event and self.scan_stop_event.is_set()):
                self.master.after(0, self.populate_treeview_from_results) # 在主线程中更新Treeview
                set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_LAST_FOLDER, folder_to_scan)
                self.master.after(0, self.log_message, f"当前扫描文件夹 '{folder_to_scan}' 已记录以备下次使用。", "INFO")

        except InterruptedError:
            self.master.after(0, self.log_message, "查找操作被用户中止。", "WARNING")
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.master.after(0, self.log_message, f"查找重复文件时发生意外错误: {e}\\n{tb_str}", "ERROR")
        finally:
            self.master.after(0, self._finalize_scan_ui_update)

    def _finalize_scan_ui_update(self):
        self.find_button.configure(state=tk.NORMAL, text="1. 查找重复文件")
        self.stop_button.configure(state=tk.DISABLED)
        if self.found_duplicate_groups:
             self.move_button.configure(state=tk.NORMAL)
        self.scan_stop_event = None 
        self.current_scan_thread = None

    def populate_treeview_from_results(self):
        self.clear_results() # 清空旧的Treeview项
        
        if not self.found_duplicate_groups or not isinstance(self.found_duplicate_groups, list):
            self.log_message("没有找到重复文件组，或结果格式不正确，无法填充列表。", "INFO" if not self.found_duplicate_groups else "ERROR")
            self.move_button.configure(state=tk.DISABLED)
            return

        if self.found_duplicate_groups and not isinstance(self.found_duplicate_groups[0], DuplicateGroup):
             self.log_message(f"结果格式不正确，期望DuplicateGroup列表，实际为 {type(self.found_duplicate_groups[0])}。", "ERROR")
             self.move_button.configure(state=tk.DISABLED)
             return

        group_display_counter = 0
        for group_data in self.found_duplicate_groups: # self.found_duplicate_groups 现在是 List[DuplicateGroup]
            group_display_counter += 1
            group_id = f"group_{group_display_counter}"
            
            level_str = group_data.level.value if group_data.level else "N/A"
            score_str = f"{group_data.score:.1f}" if hasattr(group_data, 'score') else "N/A"
            reasons_str = ", ".join(set(group_data.reasons)) if group_data.reasons else "无特定原因"
            num_files_str = f"{len(group_data.files)}个文件"

            # 父项: 显示组信息
            # "item_name", "item_path", "item_size", "item_duration", "group_info"
            group_item_values = (
                f"{level_str} ({num_files_str})", # item_name (组的概览，更简洁)
                "", # item_path (组级别留空)
                "", # item_size (组级别留空)
                "", # item_duration (组级别留空)
                f"评分: {score_str} | {reasons_str[:70]}{'...' if len(reasons_str)>70 else ''}" # group_info, 稍微加长原因显示
            )
            parent_item_id = self.tree.insert("", tk.END, iid=group_id, open=True, values=group_item_values, tags=('group_item', 'group_row_tag')) # 添加一个特定的tag用于样式

            # 子项: 显示组内每个文件的详细信息
            if group_data.files and isinstance(group_data.files[0], FileMetadata):
                for file_idx, file_meta in enumerate(group_data.files):
                    file_item_id = f"{group_id}_file_{file_idx}"
                    
                    filename = os.path.basename(file_meta.path)
                    filepath_str = os.path.dirname(file_meta.path)
                    
                    filesize_bytes = file_meta.size
                    if filesize_bytes is None: filesize_str = "N/A"
                    elif filesize_bytes >= 1024*1024*1024: filesize_str = f"{filesize_bytes / (1024*1024*1024):.2f} GB"
                    elif filesize_bytes >= 1024*1024: filesize_str = f"{filesize_bytes / (1024*1024):.2f} MB"
                    elif filesize_bytes >= 1024: filesize_str = f"{filesize_bytes / 1024:.1f} KB"
                    else: filesize_str = f"{filesize_bytes} B"
                    
                    duration_seconds = file_meta.duration
                    if duration_seconds is None: duration_str = ""
                    else:
                        td = datetime.timedelta(seconds=int(duration_seconds))
                        hours, remainder = divmod(td.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        if td.days > 0: duration_str = f"{td.days}天 {hours:02}:{minutes:02}:{seconds:02}"
                        elif hours > 0: duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                        else: duration_str = f"{minutes:02}:{seconds:02}"
                    
                    file_item_values = (
                        filename,
                        filepath_str,
                        filesize_str,
                        duration_str,
                        "" # group_info (文件级别留空)
                    )
                    try:
                        self.tree.insert(parent_item_id, tk.END, iid=file_item_id, values=file_item_values, tags=('file_item',))
                    except Exception as e_insert:
                        self.log_message(f"[Tree Populate] FAILED to insert file: {file_item_id}. Error: {e_insert}", "ERROR")

        self.tree.tag_configure('group_row_tag', background='#E8E8E8') # 默认浅灰色背景，需测试在不同主题下的效果
        # 如果是暗色主题，可能需要不同的颜色
        # try:
        #     if ctk.get_appearance_mode().lower() == "dark":
        #         self.tree.tag_configure('group_row_tag', background='#333333') # 暗色主题下的深灰色
        # except AttributeError: # ctk 可能还没完全初始化
        #     pass

        if self.found_duplicate_groups:
            self.move_button.configure(state=tk.NORMAL)
        else:
            self.move_button.configure(state=tk.DISABLED)
            self.log_message("没有在Treeview中展示任何重复文件组。", "INFO")
            
    def move_duplicates_action(self):
        if not self.found_duplicate_groups or not self.selected_folder_for_scan:
            messagebox.showwarning("无操作", "没有找到可移动的重复文件，或者未指定扫描文件夹。")
            return

        
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
        self.find_button.configure(state=tk.DISABLED)
        self.update_idletasks()
        
        moved_count_total = 0
        error_count_total = 0
        groups_processed = 0

        for hash_val, paths in list(self.found_duplicate_groups.items()):
            if len(paths) > 1:
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
        
        
        self.clear_results()
        self.find_button.configure(state=tk.NORMAL, text="1. 查找重复文件")

    def stop_scan_action(self):
        if self.scan_stop_event:
            self.log_message("正在尝试终止扫描...", level="WARNING")
            self.scan_stop_event.set()
            self.stop_button.configure(state=tk.DISABLED, text="正在终止...")
        else:
            self.log_message("没有正在运行的扫描任务可以终止。", level="INFO")

    def on_treeview_select(self, event):
        """处理Treeview中的行选择事件，在details_text_area显示选中项的'重复信息'列内容"""
        selected_items = self.tree.selection()
        self.details_text_area.configure(state=tk.NORMAL)
        self.details_text_area.delete("1.0", tk.END)

        if not selected_items:
            self.details_text_area.configure(state=tk.DISABLED)
            return

        selected_iid = selected_items[0]
        
        try:
            item_values = self.tree.item(selected_iid, "values")
            if not item_values:
                 self.details_text_area.configure(state=tk.DISABLED)
                 return

            group_info_column_index = self.tree_columns.index("group_info") # Get index dynamically
            
            detail_text_to_display = ""

            if len(item_values) > group_info_column_index:
                current_item_group_info = item_values[group_info_column_index]
                tags = self.tree.item(selected_iid, "tags")

                if 'file_item' in tags:
                    # If a file item is selected, display its parent's (group's) group_info
                    parent_iid = self.tree.parent(selected_iid)
                    if parent_iid:
                        parent_values = self.tree.item(parent_iid, "values")
                        if parent_values and len(parent_values) > group_info_column_index:
                            detail_text_to_display = parent_values[group_info_column_index]
                        else:
                            detail_text_to_display = "父组信息不完整。"
                    else:
                        detail_text_to_display = "无法找到父组信息。"
                elif 'group_item' in tags:
                    # If a group item is selected, display its own group_info
                    detail_text_to_display = current_item_group_info
                else:
                    # Should not happen if tags are set correctly
                    detail_text_to_display = current_item_group_info # Fallback to current item's info
            
            self.details_text_area.insert(tk.END, detail_text_to_display if detail_text_to_display else "无重复信息可显示。")

        except Exception as e:
            self.details_text_area.insert(tk.END, f"加载重复信息时出错: {e}")
            self.log_message(f"on_treeview_select 发生错误: {e}", "ERROR")
        
        self.details_text_area.configure(state=tk.DISABLED)

if __name__ == '__main__':
    try:
        from DUMMY_CUSTOMTKINTER_APP_FOR_TESTING import run_test_app
    except ImportError:
        class SimpleTestApp(customtkinter.CTk):
            def __init__(self, tool_frame_class):
                super().__init__()
                self.title(f"Test - {tool_frame_class.TOOL_NAME}")
                self.geometry("800x700")
                
                customtkinter.set_appearance_mode("System") # 或 "Dark" 或 "Light"
                customtkinter.set_default_color_theme("blue") # 或 "green" 或 "dark-blue"

                self.tool_frame = tool_frame_class(self)
                self.tool_frame.pack(expand=True, fill="both")

        app = SimpleTestApp(ToolPluginFrame)
        app.mainloop()
        sys.exit() # 确保干净退出

    
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