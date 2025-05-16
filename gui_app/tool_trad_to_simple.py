import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from opencc import OpenCC

# Logic function (formerly in main_gui.py)
def convert_traditional_to_simplified_logic(input_path, output_path):
    cc = OpenCC('t2s')
    try:
        with open(input_path, 'r', encoding='utf-8') as f_in, \
             open(output_path, 'w', encoding='utf-8') as f_out:
            traditional_text = f_in.read()
            simplified_text = cc.convert(traditional_text)
            f_out.write(simplified_text)
        return True, f"文件已成功转换为简体并保存至:\n{output_path}"
    except FileNotFoundError:
        return False, f"错误: 输入文件未找到 {input_path}"
    except Exception as e:
        return False, f"转换失败: {e}"


class TraditionalToSimplifiedFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        # Input File Selection
        input_file_frame = ctk.CTkFrame(self)
        input_file_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        input_file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_file_frame, text="选择繁体文件:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.input_file_entry = ctk.CTkEntry(input_file_frame, placeholder_text='点击"浏览"选择文件')
        self.input_file_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(input_file_frame, text="浏览", width=80, command=self.browse_input_file).grid(row=0, column=2, padx=(0,10), pady=10)

        # Action Button
        ctk.CTkButton(self, text="转换为简体并保存", command=self.convert_file).grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Status Label
        self.status_label = ctk.CTkLabel(self, text="", text_color="green")
        self.status_label.grid(row=2, column=0, padx=10, pady=(0,10), sticky="ew")

    def browse_input_file(self):
        file_path = filedialog.askopenfilename(
            title="选择繁体文本文件",
            filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*"))
        )
        if file_path:
            self.input_file_entry.delete(0, tk.END)
            self.input_file_entry.insert(0, file_path)
            self.status_label.configure(text="")

    def convert_file(self):
        input_path = self.input_file_entry.get()
        if not input_path:
            messagebox.showerror("错误", "请先选择一个文件！")
            self.status_label.configure(text="错误: 请选择文件", text_color="red")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("错误", f"文件不存在: {input_path}")
            self.status_label.configure(text=f"错误: 文件不存在 {input_path}", text_color="red")
            return

        path_parts = os.path.splitext(input_path)
        suggested_output_filename = f"{os.path.basename(path_parts[0])}_simplified{path_parts[1]}"
        output_path = filedialog.asksaveasfilename(
            title="保存为简体文件",
            initialfile=suggested_output_filename,
            defaultextension=path_parts[1],
            filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"),("All files", "*.*"))
        )

        if not output_path:
            self.status_label.configure(text="操作取消: 未选择保存路径", text_color="orange")
            return
        
        success, message = convert_traditional_to_simplified_logic(input_path, output_path)

        if success:
            self.status_label.configure(text=message, text_color="green")
            messagebox.showinfo("成功", message)
        else:
            self.status_label.configure(text=message, text_color="red")
            messagebox.showerror("转换失败", message) 