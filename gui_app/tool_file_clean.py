import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

# Adjust sys.path to allow importing from the parent directory (toolbox)
# This allows access to the 'file' module from 'gui_app'
# This might not be needed if the script is run as part of a package or with PYTHONPATH set
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file.file_clean_useless_name import clean_directory_filenames, PATTERNS_TO_CLEAN

class FileCleanFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # For log textbox

        # Folder Selection
        folder_sel_frame = ctk.CTkFrame(self)
        folder_sel_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        folder_sel_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_sel_frame, text="选择文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_sel_frame, placeholder_text='点击"浏览"选择文件夹')
        self.folder_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(folder_sel_frame, text="浏览", width=80, command=self.browse_folder).grid(row=0, column=2, padx=(0,10), pady=10)

        # Action Button
        ctk.CTkButton(self, text="开始清理文件名", command=self.clean_filenames_action).grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Status/Log
        self.status_label = ctk.CTkLabel(self, text="清理选定文件夹内文件的无用字符。", wraplength=480)
        self.status_label.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
        
        self.log_textbox = ctk.CTkTextbox(self, height=100, wrap=tk.WORD)
        self.log_textbox.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("1.0", "清理日志将显示在此处：\n")
        self.log_textbox.configure(state="disabled")

    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择要清理文件名的文件夹")
        if folder_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            self.status_label.configure(text="文件夹已选择。")
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", tk.END)
            self.log_textbox.insert("1.0", "清理日志将显示在此处：\n")
            self.log_textbox.configure(state="disabled")

    def clean_filenames_action(self):
        folder_path = self.folder_entry.get()
        if not folder_path:
            messagebox.showerror("错误", "请先选择一个文件夹！")
            self.status_label.configure(text="错误: 请选择文件夹", text_color="red")
            return

        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", f"无效的文件夹路径: {folder_path}")
            self.status_label.configure(text=f"错误: 无效的文件夹路径", text_color="red")
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END) 
        self.log_textbox.insert("1.0", f"开始清理文件夹: {folder_path}\n---\n")
        self.update_idletasks()

        # Call the imported logic function
        # Using default patterns for now, could add UI to configure this later
        log_messages, renamed_count, processed_count, errors = clean_directory_filenames(folder_path, PATTERNS_TO_CLEAN)
        
        for msg in log_messages:
            self.log_textbox.insert(tk.END, msg + "\n")
        
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

        summary_for_status = f"完成: 处理{processed_count}, 重命名{renamed_count}, 错误/警告{len(errors)}."
        final_message_box_summary = f"文件名清理操作完成。\n处理文件数: {processed_count}\n重命名文件数: {renamed_count}\n错误/警告数: {len(errors)}\n\n详情请查看日志面板。"

        if errors:
            self.status_label.configure(text=summary_for_status, text_color="orange")
            messagebox.showwarning("完成 (有警告/错误)", final_message_box_summary)
        elif renamed_count > 0:
            self.status_label.configure(text=summary_for_status, text_color="green")
            messagebox.showinfo("完成", final_message_box_summary)
        else:
            self.status_label.configure(text=summary_for_status, text_color="green")
            messagebox.showinfo("完成", final_message_box_summary) 