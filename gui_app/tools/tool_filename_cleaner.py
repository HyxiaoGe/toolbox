import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = current_dir
gui_app_dir = os.path.dirname(tools_dir)
project_root = os.path.dirname(gui_app_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from file import file_clean_useless_name # 后端逻辑

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "文件名清理"
    TOOL_ORDER = 20

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 允许日志区域扩展

        self.dir_frame = ctk.CTkFrame(self)
        self.dir_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        self.dir_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.dir_frame, text="选择要清理的文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.dir_entry = ctk.CTkEntry(self.dir_frame, placeholder_text='点击"浏览"选择文件夹')
        self.dir_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(self.dir_frame, text="浏览", width=80, command=self.browse_directory).grid(row=0, column=2, padx=(0,10), pady=10)

        self.clean_button = ctk.CTkButton(self, text="开始清理选定文件夹中的文件名", command=self.clean_filenames_in_directory)
        self.clean_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.log_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15, undo=True, state=tk.DISABLED)
        self.log_text_area.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")
        self._apply_theme_to_scrolledtext(self.log_text_area)

    def _apply_theme_to_scrolledtext(self, text_widget):
        try:
            fg_color = ctk.ThemeManager.theme["CTkTextbox"]["fg_color"]
            text_color = ctk.ThemeManager.theme["CTkTextbox"]["text_color"]
            is_dark = ctk.get_appearance_mode().lower() == "dark"
            current_fg_color = fg_color[1] if isinstance(fg_color, list) and is_dark else fg_color[0] if isinstance(fg_color, list) else fg_color
            current_text_color = text_color[1] if isinstance(text_color, list) and is_dark else text_color[0] if isinstance(text_color, list) else text_color
            text_widget.config(
                background=current_fg_color,
                foreground=current_text_color,
                insertbackground=current_text_color, 
                font=("Segoe UI", 13),
                relief=tk.FLAT, 
                borderwidth=ctk.ThemeManager.theme["CTkTextbox"]["border_width"],
                padx=5, pady=5 
            )
        except Exception as e:
            print(f"Error applying theme to ScrolledText: {e}")
            text_widget.config(font=("Arial", 12))
            pass

    def browse_directory(self):
        directory_path = filedialog.askdirectory(title="选择文件夹")
        if directory_path:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory_path)
            self.log_text_area.configure(state=tk.NORMAL)
            self.log_text_area.delete("1.0", tk.END)
            self.log_text_area.insert(tk.END, f"已选择文件夹: {directory_path}\n")
            self.log_text_area.configure(state=tk.DISABLED)

    def log_message(self, message, color="black"):
        self.log_text_area.configure(state=tk.NORMAL)
        self.log_text_area.insert(tk.END, message + "\n")
        self.log_text_area.see(tk.END)
        self.log_text_area.configure(state=tk.DISABLED)

    def clean_filenames_in_directory(self):
        directory = self.dir_entry.get()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("错误", "请选择一个有效的文件夹！")
            return

        self.log_text_area.configure(state=tk.NORMAL)
        self.log_text_area.delete("1.0", tk.END)
        self.log_message(f"开始清理文件夹 '{directory}' 中的文件名...")
        self.log_text_area.configure(state=tk.DISABLED)
        self.update_idletasks()

        try:
            logs, cleaned_count, skipped_count, error_count = file_clean_useless_name.clean_directory_filenames(directory, log_callback=self.log_message)
            
            summary_message = f"文件名清理完成。\n清理成功: {cleaned_count} 个文件。\n跳过/无需更改: {skipped_count} 个文件。\n发生错误: {error_count} 个文件。"
            self.log_message(summary_message)
            if error_count > 0:
                messagebox.showwarning("完成伴有错误", f"{summary_message}\n部分文件清理失败，请检查日志。")
            else:
                messagebox.showinfo("完成", summary_message)
        except Exception as e:
            error_msg = f"执行文件名清理时发生严重错误: {e}"
            self.log_message(error_msg)
            messagebox.showerror("严重错误", error_msg) 