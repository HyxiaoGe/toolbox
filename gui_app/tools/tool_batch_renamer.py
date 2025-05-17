import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import sys
import os
import re # 如果需要，用于模式验证，或用于重命名逻辑

# 调整 sys.path 以包含项目根目录，以便导入后端模块
# __file__ 是 gui_app/tools/tool_batch_renamer.py
# project_root 应该是 gui_app 的父目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from file import file_rename # 后端逻辑

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "批量文件重命名"
    TOOL_ORDER = 30

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        # 第6行 (log_text_area) 应该是主要扩展的行
        self.grid_rowconfigure(6, weight=1) 

        # --- UI 元素 ---
        # 目录选择
        dir_frame = ctk.CTkFrame(self)
        dir_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        dir_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(dir_frame, text="目标文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="选择包含要重命名文件的文件夹")
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(dir_frame, text="浏览", width=70, command=self.browse_directory).grid(row=0, column=2, padx=5, pady=5)

        # 重命名选项框架
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)
        # options_frame.grid_columnconfigure(3, weight=1) # 目前仅有效使用2列用于模式

        ctk.CTkLabel(options_frame, text="原文件名匹配 (可选):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.match_pattern_entry = ctk.CTkEntry(options_frame, placeholder_text="例如: *.jpg (glob) 或 data_(\\d+).txt (正则)")
        self.match_pattern_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew") # 如果稍后添加更多列，则允许其跨越

        ctk.CTkLabel(options_frame, text="新文件名模板:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.rename_pattern_entry = ctk.CTkEntry(options_frame, placeholder_text="例: img_{{num}}.{{ext}} 或 {{group1}}_{{name}}_{{date}}")
        self.rename_pattern_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(options_frame, text="占位符: {{num}}, {{name}}, {{ext}}, {{groupN}}, {{date}}, {{datetime}}", wraplength=self.winfo_width() - 40 if self.winfo_width() > 50 else 500, justify="left").grid(row=2, column=0, columnspan=4, padx=5, pady=(0,5), sticky="w")

        # 编号框架（在 options_frame 内或单独）
        num_frame = ctk.CTkFrame(options_frame) # 嵌套以便更好地控制布局
        num_frame.grid(row=3, column=0, columnspan=4, padx=0, pady=0, sticky="ew")
        num_frame.grid_columnconfigure(1, weight=1)
        num_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(num_frame, text="起始序号:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.start_num_entry = ctk.CTkEntry(num_frame, width=120)
        self.start_num_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.start_num_entry.insert(0, "1")

        ctk.CTkLabel(num_frame, text="序号步长:").grid(row=0, column=2, padx=(10,5), pady=5, sticky="w")
        self.step_num_entry = ctk.CTkEntry(num_frame, width=120)
        self.step_num_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.step_num_entry.insert(0, "1")

        # 操作按钮
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        self.preview_button = ctk.CTkButton(action_frame, text="预览重命名效果", command=self.preview_rename)
        self.preview_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.rename_button = ctk.CTkButton(action_frame, text="执行重命名", command=self.execute_rename, state=tk.DISABLED)
        self.rename_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 预览区域 (Treeview)
        preview_label = ctk.CTkLabel(self, text="预览 (最多显示前100项):")
        preview_label.grid(row=3, column=0, padx=10, pady=(5,0), sticky="w")
        
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) # 使 Treeview 区域垂直扩展

        self.preview_tree = ttk.Treeview(tree_frame, columns=("Original", "New"), show="headings", height=5)
        self.preview_tree.heading("Original", text="原文件名")
        self.preview_tree.heading("New", text="新文件名")
        self.preview_tree.column("Original", width=250, stretch=tk.YES)
        self.preview_tree.column("New", width=250, stretch=tk.YES)
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        
        tree_scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=tree_scrollbar_y.set)
        tree_scrollbar_y.grid(row=0, column=1, sticky="ns")
        
        tree_scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(xscrollcommand=tree_scrollbar_x.set)
        tree_scrollbar_x.grid(row=1, column=0, sticky="ew")

        # 日志显示区域
        log_label = ctk.CTkLabel(self, text="日志:")
        log_label.grid(row=5, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w") # 如果滚动条在外部，则列跨度为2
        self.log_text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=6, undo=True, state=tk.DISABLED)
        self.log_text_area.grid(row=6, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nsew")
        # self.grid_rowconfigure(6, weight=1) # 已在 __init__ 顶部设置
        self._apply_theme_to_scrolledtext(self.log_text_area)

        self.rename_plan = None # 用于存储预览中的计划
        self.bind("<Configure>", self._on_configure) # 用于更新 wraplength

    def _on_configure(self, event=None):
        # 更新占位符标签的 wraplength
        # 找到标签 - 它是 options_frame 的子元素
        options_frame = self.grid_slaves(row=1, column=0)[0]
        placeholder_label = options_frame.grid_slaves(row=2, column=0)[0]
        new_width = options_frame.winfo_width() - 20 # 减去一些内边距
        if new_width > 20:
            placeholder_label.configure(wraplength=new_width)

    def _apply_theme_to_scrolledtext(self, text_widget):
        try:
            # 尝试从 CustomTkinter 的 ThemeManager 获取主题颜色
            # 此处假设 ThemeManager 的结构；如果 CTk 主题更改，可能需要调整
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
                highlightbackground=current_border, # 用于焦点边框
                highlightcolor=current_border,
                highlightthickness=border_width,
                padx=5, pady=5
            )
        except Exception as e:
            # 如果主题设置失败（例如 ThemeManager 结构已更改），则使用回退方案
            # print(f"向 ScrolledText 应用主题时出错: {e}")
            text_widget.config(font=("Arial", 11), relief=tk.SOLID, borderwidth=1) # 基本回退
            pass # 对用户保持静默

    def browse_directory(self):
        directory = filedialog.askdirectory(title="选择文件夹")
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.rename_button.configure(state=tk.DISABLED)
            self.preview_tree.delete(*self.preview_tree.get_children())
            self.log_message("已选择文件夹: " + directory, clear_previous=True)

    def log_message(self, message, clear_previous=False):
        self.log_text_area.configure(state=tk.NORMAL)
        if clear_previous:
            self.log_text_area.delete("1.0", tk.END)
        self.log_text_area.insert(tk.END, message + "\n")
        self.log_text_area.see(tk.END)
        self.log_text_area.configure(state=tk.DISABLED)

    def preview_rename(self):
        directory = self.dir_entry.get()
        match_pattern = self.match_pattern_entry.get() or None
        rename_template = self.rename_pattern_entry.get()
        try:
            start_num = int(self.start_num_entry.get())
            step_num = int(self.step_num_entry.get())
        except ValueError:
            messagebox.showerror("输入错误", "起始序号和步长必须是整数。")
            return

        if not directory or not os.path.isdir(directory):
            messagebox.showerror("输入错误", "请选择一个有效的文件夹！")
            return
        if not rename_template:
            messagebox.showerror("输入错误", "新文件名模板不能为空！")
            return

        self.log_message(f"开始预览: 文件夹='{directory}', 匹配='{match_pattern}', 新模板='{rename_template}'", clear_previous=True)
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.rename_button.configure(state=tk.DISABLED)
        self.rename_plan = None

        try:
            self.preview_button.configure(state=tk.DISABLED, text="正在预览...")
            self.update_idletasks() # 确保按钮文本更新
            
            success, plan_or_error, logs = file_rename.generate_rename_plan(
                directory,
                rename_template,
                match_pattern,
                start_num,
                step_num
            )
            for log_entry in logs:
                self.log_message(log_entry)
            
            if success:
                self.rename_plan = plan_or_error
                if not self.rename_plan:
                    self.log_message("预览完成：没有文件符合匹配条件或无需重命名。")
                    messagebox.showinfo("预览完成", "没有文件符合匹配条件或无需重命名。")
                else:
                    for i, (orig, new) in enumerate(self.rename_plan):
                        if i < 100: # 限制预览显示
                            self.preview_tree.insert("", tk.END, values=(os.path.basename(orig), os.path.basename(new)))
                        elif i == 100:
                            self.preview_tree.insert("", tk.END, values=("... (更多项目未显示)", "..."))
                            break # 停止向 Treeview 添加
                    self.log_message(f"预览完成，计划重命名 {len(self.rename_plan)} 个文件。")
                    self.rename_button.configure(state=tk.NORMAL)
            else:
                self.log_message(f"预览失败: {plan_or_error}")
                messagebox.showerror("预览失败", f"生成重命名计划时出错:\n{plan_or_error}")
        except Exception as e:
            self.log_message(f"预览过程中发生意外错误: {e}")
            messagebox.showerror("预览错误", f"预览时发生意外错误: {e}")
        finally:
            self.preview_button.configure(state=tk.NORMAL, text="预览重命名效果")

    def execute_rename(self):
        if not self.rename_plan:
            messagebox.showerror("执行错误", "没有可执行的重命名计划。请先成功预览。")
            return

        confirm = messagebox.askyesno("确认重命名", f"即将按计划重命名 {len(self.rename_plan)} 个文件。此操作通常无法轻易撤销。\n\n是否继续？", icon=messagebox.WARNING)
        if not confirm:
            self.log_message("用户取消了重命名操作。")
            return

        self.log_message("开始执行重命名操作...")
        self.rename_button.configure(state=tk.DISABLED, text="正在重命名...")
        self.preview_button.configure(state=tk.DISABLED) # 执行期间禁用预览
        self.update_idletasks()

        try:
            # 将 self.log_message 作为回调传递给后端
            success, summary_message, detailed_logs = file_rename.execute_rename_plan(
                self.rename_plan, 
                log_callback=lambda msg: self.log_message(f"[执行] {msg}") 
            )
            
            # The backend now returns all logs, including those from the callback.
            # So, we might not need to iterate `detailed_logs` if `log_message` was called for each.
            # However, the final summary_message is important.
            # Let's clear and re-log if the backend provides a full log list for clarity.
            # For now, the lambda above prefixes [执行] to backend logs.
            # The final summary message will be logged without the prefix below.

            self.log_message(f"执行完毕。最终总结: {summary_message}") # Display final summary from backend
            
            if success:
                messagebox.showinfo("完成", summary_message)
            else:
                # Even if overall success is False (e.g. some errors), summary_message will reflect this.
                messagebox.showwarning("重命名注意", summary_message) # Use warning if not all successful

        except Exception as e:
            self.log_message(f"执行重命名过程中发生意外错误: {e}")
            messagebox.showerror("执行错误", f"执行重命名时发生意外错误: {e}")
        finally:
            self.rename_plan = None # Clear plan
            self.preview_tree.delete(*self.preview_tree.get_children()) # Clear preview
            self.rename_button.configure(state=tk.DISABLED, text="执行重命名") # Keep rename button disabled until next preview
            self.preview_button.configure(state=tk.NORMAL)

if __name__ == '__main__':
    # 示例用法（用于直接测试此框架）
    try:
        from DUMMY_CUSTOMTKINTER_APP_FOR_TESTING import run_test_app
    except ImportError:
        # 如果虚拟应用程序不可用，则使用回退
        # 创建一个简单的 CTk 应用以进行测试
        class SimpleTestApp(ctk.CTk):
            def __init__(self, tool_frame_class):
                super().__init__()
                self.title(f"Test - {tool_frame_class.TOOL_NAME}")
                self.geometry("800x700")
                
                # 确保主题已加载（如果尚未加载）
                ctk.set_appearance_mode("System") # 或 "Dark" 或 "Light"
                ctk.set_default_color_theme("blue") # 或 "green" 或 "dark-blue"

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

