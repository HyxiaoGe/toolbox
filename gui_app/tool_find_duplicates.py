import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys

# Adjust sys.path to include the parent directory (toolbox)
# This allows importing modules from the 'file' and 'software' directories
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, '..')
sys.path.append(parent_dir)

from file.file_find_duplicates import collect_duplicate_files_info, move_files_to_duplicate_folder

class FindDuplicatesFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        # --- UI Elements ---
        self.folder_path_var = tk.StringVar()
        self.found_duplicate_groups = {}
        self.selected_folder_for_scan = ""

        # Folder selection
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="目标文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_frame, textvariable=self.folder_path_var, width=300)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ctk.CTkButton(folder_frame, text="浏览", command=self.browse_folder)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        # Action buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1) # Distribute space for buttons
        action_frame.grid_columnconfigure(1, weight=1)

        self.find_button = ctk.CTkButton(action_frame, text="1. 查找重复文件", command=self.find_duplicates_action)
        self.find_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.move_button = ctk.CTkButton(action_frame, text="2. 移动选中重复项 (谨慎操作!)", command=self.move_duplicates_action, state="disabled")
        self.move_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Results and Logs Area
        results_log_frame = ctk.CTkFrame(self)
        results_log_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")
        results_log_frame.grid_rowconfigure(0, weight=1) # Make treeview expand
        results_log_frame.grid_columnconfigure(0, weight=1) # Make treeview expand
        self.grid_rowconfigure(2, weight=1) # Allow this frame to expand vertically

        # Treeview for displaying duplicate groups
        self.tree = ttk.Treeview(results_log_frame, columns=("hash", "count", "files"), show='headings')
        self.tree.heading("hash", text="哈希 (部分)")
        self.tree.heading("count", text="数量")
        self.tree.heading("files", text="文件列表")
        self.tree.column("hash", width=100, stretch=tk.NO)
        self.tree.column("count", width=50, stretch=tk.NO, anchor='center')
        self.tree.column("files", width=400)
        self.tree.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Log Textbox
        self.log_textbox = ctk.CTkTextbox(self, height=150, wrap=tk.WORD)
        self.log_textbox.grid(row=3, column=0, padx=10, pady=10, sticky="ew") 

        self.log_to_textbox("请选择要扫描重复文件的文件夹。图片和视频文件将被比较。")
        self.log_to_textbox("注意: 移动操作会将文件整理到所选文件夹下的 'duplicates_found' 子目录中。")

    def log_to_textbox(self, message):
        if not message.endswith("\n"):
            message += "\n"
        self.log_textbox.insert(tk.END, message)
        self.log_textbox.see(tk.END)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.selected_folder_for_scan = folder_selected
            self.log_to_textbox(f"已选择文件夹: {folder_selected}")
            self.clear_results()
            self.move_button.configure(state="disabled")

    def clear_results(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.found_duplicate_groups = {}

    def find_duplicates_action(self):
        folder_to_scan = self.folder_path_var.get()
        if not folder_to_scan or not os.path.isdir(folder_to_scan):
            messagebox.showerror("错误", "请选择一个有效的文件夹进行扫描。")
            return

        self.selected_folder_for_scan = folder_to_scan # Store for move action
        self.log_to_textbox(f"开始在 {folder_to_scan} 中查找重复文件...")
        self.clear_results()
        self.find_button.configure(state="disabled")
        self.move_button.configure(state="disabled")
        self.update_idletasks() # Ensure UI updates

        try:
            # Call the refactored logic
            duplicate_groups, logs, processed, skipped_unsupported, skipped_errors = collect_duplicate_files_info(folder_to_scan)
            
            for log_entry in logs:
                self.log_to_textbox(log_entry)
            
            self.found_duplicate_groups = duplicate_groups # Store for potential move action

            if not duplicate_groups:
                self.log_to_textbox("扫描完成，未找到重复文件组。")
            else:
                self.log_to_textbox(f"扫描完成。找到了 {len(duplicate_groups)} 组重复文件。详情如下:")
                for i, (hash_val, paths) in enumerate(duplicate_groups.items()):
                    # Ensure paths are strings for display, just in case
                    files_str = ", ".join([os.path.basename(p) for p in paths]) 
                    self.tree.insert("", tk.END, iid=str(i), values=(hash_val[:12] + "...", len(paths), files_str))
                    # Store full path info with tree item for later use if needed, though not directly used in this example for selection
                    self.tree.item(str(i), tags=(hash_val,))
                self.move_button.configure(state="normal") # Enable move button only if duplicates found

        except Exception as e:
            self.log_to_textbox(f"查找重复文件时发生错误: {e}")
            messagebox.showerror("查找失败", f"发生错误: {e}")
        finally:
            self.find_button.configure(state="normal")

    def move_duplicates_action(self):
        if not self.found_duplicate_groups:
            messagebox.showinfo("无操作", "没有找到可移动的重复文件组。请先运行查找。")
            return
        
        if not self.selected_folder_for_scan:
            messagebox.showerror("错误", "无法确定原始扫描文件夹以创建 'duplicates_found' 目录。请重新扫描。")
            return

        confirm = messagebox.askyesno("确认移动", 
                                      f"确定要将找到的重复文件移动到 "
                                      f"'{os.path.join(self.selected_folder_for_scan, 'duplicates_found')}' 子目录吗？\n\n"
                                      f"此操作不可轻易撤销！")
        if not confirm:
            self.log_to_textbox("移动操作已取消。")
            return

        self.log_to_textbox(f"开始移动重复文件...")
        self.move_button.configure(state="disabled")
        self.find_button.configure(state="disabled") # Disable find during move
        self.update_idletasks()

        try:
            # Call the refactored move logic
            move_logs, moved_count = move_files_to_duplicate_folder(self.found_duplicate_groups, self.selected_folder_for_scan)
            
            for log_entry in move_logs:
                self.log_to_textbox(log_entry)
            
            if moved_count > 0:
                messagebox.showinfo("移动成功", f"成功移动了 {moved_count} 个文件。")
                self.log_to_textbox(f"成功移动了 {moved_count} 个文件。请检查 'duplicates_found' 文件夹。")
            else:
                messagebox.showinfo("移动完成", "文件移动过程完成，但没有文件被实际移动（可能已不存在或之前已移动）。详情请查看日志。")
            
            # Clear results and disable move button as the state has changed
            self.clear_results()
            # self.found_duplicate_groups = {} # Already cleared in clear_results

        except Exception as e:
            self.log_to_textbox(f"移动重复文件时发生错误: {e}")
            messagebox.showerror("移动失败", f"发生错误: {e}")
        finally:
            self.move_button.configure(state="disabled") # Always disable after attempt, user should re-scan
            self.find_button.configure(state="normal")
            # After moving, the user should ideally re-scan if they want to see the current state.
            self.log_to_textbox("移动操作完成。建议重新扫描文件夹以更新视图。")

if __name__ == '__main__':
    # This is for testing the frame independently
    root = ctk.CTk()
    root.title("Test Find Duplicates Frame")
    root.geometry("700x700")
    frame = FindDuplicatesFrame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    root.mainloop() 