import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

# Adjust sys.path to allow importing from the parent directory (toolbox)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file.file_rename import rename_files_in_directory

class BatchRenameFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # For log

        # Folder Selection
        folder_sel_frame = ctk.CTkFrame(self)
        folder_sel_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        folder_sel_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_sel_frame, text="目标文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_sel_frame, placeholder_text='点击"浏览"选择文件夹')
        self.folder_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(folder_sel_frame, text="浏览", width=80, command=self.browse_folder).grid(row=0, column=2, padx=(0,10), pady=10)

        # Rename Pattern/Prefix
        pattern_frame = ctk.CTkFrame(self)
        pattern_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        pattern_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pattern_frame, text="新文件名前缀:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.pattern_entry = ctk.CTkEntry(pattern_frame, placeholder_text="例如 'MyImage_'")
        self.pattern_entry.grid(row=0, column=1, padx=(0,10), pady=5, sticky="ew")
        self.pattern_entry.insert(0, "RenamedFile_")

        # Action Button
        ctk.CTkButton(self, text="批量重命名文件", command=self.rename_action).grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # Log Textbox
        self.log_textbox = ctk.CTkTextbox(self, wrap=tk.WORD)
        self.log_textbox.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.log_textbox.insert("1.0", "重命名日志将显示在此处...\n")
        self.log_textbox.configure(state="disabled")
        
    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择要批量重命名文件的文件夹")
        if folder_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", tk.END)
            self.log_textbox.insert("1.0", "重命名日志将显示在此处...\n")
            self.log_textbox.configure(state="disabled")

    def rename_action(self):
        folder_path = self.folder_entry.get()
        new_name_prefix = self.pattern_entry.get()

        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("错误", "请选择一个有效的文件夹！")
            return
        if not new_name_prefix:
            messagebox.showerror("错误", "请输入文件名前缀！")
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.insert("1.0", f"开始批量重命名文件夹 '{folder_path}' 内的文件，使用前缀 '{new_name_prefix}'\n---\n")
        self.update_idletasks()

        # Call the imported logic function from file.file_rename
        log_messages, renamed_files_count, errors_list = rename_files_in_directory(folder_path, new_name_prefix)

        for msg in log_messages:
            self.log_textbox.insert(tk.END, msg + "\n")
        
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

        final_summary_text = f"批量重命名操作完成。\n重命名文件数: {renamed_files_count}\n错误数: {len(errors_list)}\n\n详情请查看日志面板。"

        if errors_list:
            messagebox.showwarning("完成 (有错误)", final_summary_text)
        elif renamed_files_count > 0:
            messagebox.showinfo("完成", final_summary_text)
        else: # No errors, no files renamed (e.g., empty folder or no files matched criteria if any)
            messagebox.showinfo("完成", final_summary_text) 