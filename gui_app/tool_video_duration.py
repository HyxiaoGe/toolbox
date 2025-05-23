import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file.file_duration_statistics import sum_mp4_durations_in_directory, DEFAULT_FFPROBE_PATH, format_duration_to_hhmmss

class VideoDurationFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ffprobe_frame = ctk.CTkFrame(self)
        ffprobe_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        ffprobe_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ffprobe_frame, text="FFprobe路径:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.ffprobe_entry = ctk.CTkEntry(ffprobe_frame, placeholder_text="例如 D:\\ffmpeg\\bin\\ffprobe.exe")
        self.ffprobe_entry.grid(row=0, column=1, padx=(0,10), pady=5, sticky="ew")
        self.ffprobe_entry.insert(0, DEFAULT_FFPROBE_PATH) 

        folder_sel_frame = ctk.CTkFrame(self)
        folder_sel_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        folder_sel_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_sel_frame, text="MP4文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_sel_frame, placeholder_text='点击"浏览"选择文件夹')
        self.folder_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(folder_sel_frame, text="浏览", width=80, command=self.browse_folder).grid(row=0, column=2, padx=(0,10), pady=10)

        ctk.CTkButton(self, text="统计MP4总时长", command=self.calculate_duration_action).grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.log_textbox = ctk.CTkTextbox(self, wrap=tk.WORD)
        self.log_textbox.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.log_textbox.insert("1.0", "请指定ffprobe.exe的正确路径。\n处理日志和结果将显示在此处...\n")
        self.log_textbox.configure(state="disabled")

    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含MP4文件的文件夹 (将递归扫描)")
        if folder_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", tk.END)
            self.log_textbox.insert("1.0", "日志区域已清空，等待操作...\n")
            self.log_textbox.configure(state="disabled")

    def calculate_duration_action(self):
        folder_path = self.folder_entry.get()
        ffprobe_path = self.ffprobe_entry.get()

        if not folder_path:
            messagebox.showerror("错误", "请先选择一个文件夹！")
            return
        if not ffprobe_path:
            messagebox.showerror("错误", "请提供ffprobe.exe的路径！")
            return
        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", f"无效的文件夹路径: {folder_path}")
            return
        if not os.path.isfile(ffprobe_path):
            messagebox.showerror("错误", f"ffprobe.exe 未在指定路径找到: \n{ffprobe_path}\n请检查路径是否正确。")
            return
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.insert("1.0", f"开始统计 '{folder_path}' 中的MP4文件总时长...\n使用ffprobe: '{ffprobe_path}'\n---\n")
        self.update_idletasks()

        total_seconds, processed_count, log_messages, errors_list = sum_mp4_durations_in_directory(folder_path, ffprobe_path)

        for msg in log_messages:
            self.log_textbox.insert(tk.END, msg + "\n")
        
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

        formatted_total_duration = format_duration_to_hhmmss(total_seconds)
        final_summary_text = f"视频时长统计完成。\n处理MP4文件数: {processed_count}\n总时长: {formatted_total_duration}\n错误数: {len(errors_list)}\n\n详情请查看日志面板。"

        if errors_list:
            messagebox.showwarning("完成 (有错误)", final_summary_text)
        elif processed_count > 0:
            messagebox.showinfo("完成", final_summary_text)
        else:
            messagebox.showinfo("完成", final_summary_text) 