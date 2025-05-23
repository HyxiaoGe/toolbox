import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import sys
import subprocess
import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file.file_duration_statistics import sum_mp4_durations_in_directory, format_duration_to_hhmmss
from gui_app.config_manager import get_setting, set_setting

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "视频时长统计"
    TOOL_ORDER = 40
    CONFIG_KEY_FFPROBE_PATH = "ffprobe_path"
    FALLBACK_FFPROBE_PATH = r'D:\\ffmpeg-7.0-full_build\\bin\\ffprobe.exe'

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # FFprobe path
        ffprobe_frame = ctk.CTkFrame(self)
        ffprobe_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        ffprobe_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ffprobe_frame, text="FFprobe路径:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.ffprobe_path_var = tk.StringVar()
        
        saved_ffprobe_path = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_FFPROBE_PATH, self.FALLBACK_FFPROBE_PATH)
        self.ffprobe_path_var.set(saved_ffprobe_path)

        self.ffprobe_entry = ctk.CTkEntry(ffprobe_frame,textvariable=self.ffprobe_path_var, placeholder_text="例如 D:\\\\ffmpeg\\\\bin\\\\ffprobe.exe")
        self.ffprobe_entry.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ew")
        self.browse_ffprobe_button = ctk.CTkButton(ffprobe_frame, text="浏览", width=60, command=self.browse_ffprobe)
        self.browse_ffprobe_button.grid(row=0, column=2, padx=(0,10), pady=5)

        folder_sel_frame = ctk.CTkFrame(self)
        folder_sel_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        folder_sel_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_sel_frame, text="MP4文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_sel_frame, placeholder_text='点击"浏览"选择文件夹')
        self.folder_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(folder_sel_frame, text="浏览", width=80, command=self.browse_folder).grid(row=0, column=2, padx=(0,10), pady=10)

        self.action_button = ctk.CTkButton(self, text="开始统计MP4总时长", command=self.calculate_duration_action)
        self.action_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(self, orientation='horizontal', mode='indeterminate')

        log_label = ctk.CTkLabel(self, text="日志:")
        log_label.grid(row=4, column=0, padx=10, pady=(5,0), sticky="w")
        self.log_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=8, undo=True)
        self.log_text_area.grid(row=5, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.grid_rowconfigure(5, weight=1)
        self._apply_theme_to_scrolledtext(self.log_text_area)
        self.log_message("请指定ffprobe.exe的正确路径。\n处理日志和结果将显示在此处...\n", clear_log=True)
        
        if self.ffprobe_path_var.get() and not self._validate_ffprobe_path(self.ffprobe_path_var.get(), silent=True):
            self.log_message(f"警告: 从配置加载的FFprobe路径 '{self.ffprobe_path_var.get()}' 未通过版本验证。请检查路径。", is_error=True)
        elif os.path.isfile(self.ffprobe_path_var.get()):
            if self._validate_ffprobe_path(self.ffprobe_path_var.get()):
                set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_FFPROBE_PATH, self.ffprobe_path_var.get())

    def _validate_ffprobe_path(self, ffprobe_exe_path, silent=False):
        if not ffprobe_exe_path or not os.path.isfile(ffprobe_exe_path):
            if not silent:
                self.log_message(f"FFprobe路径验证失败: 文件不存在 '{ffprobe_exe_path}'", is_error=True)
            return False
        try:
            result = subprocess.run(
                [ffprobe_exe_path, "-version"],
                capture_output=True, text=True, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            output = result.stdout.strip() + result.stderr.strip()
            if result.returncode == 0 and ("ffprobe version" in output.lower() or "ffmpeg version" in output.lower()):
                if not silent:
                    self.log_message(f"FFprobe路径验证成功: {ffprobe_exe_path}")
                return True
            else:
                if not silent:
                    error_details = f"命令输出: {output[:200]}..." if output else f"返回码: {result.returncode}"
                    self.log_message(f"FFprobe路径验证失败: '{ffprobe_exe_path}' 不是有效的ffprobe执行文件. {error_details}", is_error=True)
                return False
        except FileNotFoundError:
            if not silent:
                self.log_message(f"FFprobe路径验证错误: 文件未找到(subprocess) '{ffprobe_exe_path}'", is_error=True)
            return False
        except Exception as e:
            if not silent:
                self.log_message(f"FFprobe路径验证时发生意外错误: {e}", is_error=True)
            return False

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
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {prefix}{message}\n"
        
        self.log_text_area.insert(tk.END, formatted_message)
        self.log_text_area.see(tk.END)
        self.log_text_area.configure(state=tk.DISABLED)

    def browse_ffprobe(self):
        file_path = filedialog.askopenfilename(
            title="选择 ffprobe.exe",
            filetypes=(("Executable files", "*.exe"), ("All files", "*.*"))
        )
        if file_path:
            self.ffprobe_path_var.set(file_path)
            if self._validate_ffprobe_path(file_path):
                set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_FFPROBE_PATH, file_path)

    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含MP4文件的文件夹 (将递归扫描)")
        if folder_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            self.log_message("已选择文件夹: " + folder_path + "\n等待操作...", clear_log=True)

    def calculate_duration_action(self):
        folder_path = self.folder_entry.get()
        ffprobe_path = self.ffprobe_path_var.get()

        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("错误", f"请选择一个有效的文件夹！路径: {folder_path}")
            return
        
        if not self._validate_ffprobe_path(ffprobe_path):
            messagebox.showerror("FFprobe错误", f"指定的FFprobe路径无效或不是有效的ffprobe程序: \n{ffprobe_path}\n请检查路径和程序是否正确，并查看日志获取详细信息。")
            return
        
        current_saved_path = get_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_FFPROBE_PATH)
        if ffprobe_path != current_saved_path:
            set_setting(ToolPluginFrame.TOOL_NAME, ToolPluginFrame.CONFIG_KEY_FFPROBE_PATH, ffprobe_path)
            self.log_message(f"FFprobe 路径已在运行时更新并保存: {ffprobe_path}")
        
        self.log_message(f"开始统计 '{folder_path}' 中的MP4文件总时长...\n使用ffprobe: '{ffprobe_path}'\n---", clear_log=True)
        self.action_button.configure(state=tk.DISABLED, text="正在统计...")
        
        self.progress_bar.grid(row=3, column=0, padx=10, pady=(0,5), sticky="ew")
        self.progress_bar.start()
        
        self.update_idletasks()

        try:
            total_seconds, processed_count, log_messages, errors_list = sum_mp4_durations_in_directory(folder_path, ffprobe_path)

            for msg in log_messages:
                self.log_message(msg)
        
            formatted_total_duration = format_duration_to_hhmmss(total_seconds)
            
            final_summary_for_popup = (
                f"视频时长统计完成。\n"
                f"处理MP4文件数: {processed_count}\n"
                f"总时长: {formatted_total_duration}\n"
                f"错误数: {len(errors_list)}\n\n"
                f"详情请查看日志面板。"
            )

            if errors_list:
                messagebox.showwarning("完成 (有错误)", final_summary_for_popup)
            elif processed_count > 0:
                messagebox.showinfo("完成", final_summary_for_popup)
            else:
                messagebox.showinfo("完成", final_summary_for_popup)

        except Exception as e:
            self.log_message(f"统计过程中发生意外错误: {e}", is_error=True)
            messagebox.showerror("统计错误", f"发生意外错误: {e}")
        finally:
            self.action_button.configure(state=tk.NORMAL, text="开始统计MP4总时长")
            self.progress_bar.stop()
            self.progress_bar.grid_forget() 