import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import sys
import os
from opencc import OpenCC

# 正确设置 sys.path 以便从项目根目录中的 'opencc_python' 包导入
# 假设此文件位于 gui_app/tools/
current_dir = os.path.dirname(os.path.abspath(__file__))
gui_app_dir = os.path.dirname(current_dir) # gui_app 目录
project_root = os.path.dirname(gui_app_dir) # project_root 目录
if project_root not in sys.path:
    sys.path.append(project_root)

# 由于UI现在基于文本，已移除未使用的 convert_traditional_to_simplified_logic 函数

class ToolPluginFrame(ctk.CTkFrame):
    TOOL_NAME = "文本繁简转换"
    TOOL_ORDER = 10

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # 允许 TabView 扩展

        self.tab_view = ctk.CTkTabview(self, segmented_button_selected_hover_color=ctk.ThemeManager.theme["CTkSegmentedButton"]["selected_hover_color"])
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.tab_text = self.tab_view.add("文本输入转换")
        self.tab_file = self.tab_view.add("文件批量转换")

        self._create_text_conversion_tab(self.tab_text)
        self._create_file_conversion_tab(self.tab_file)

        # 默认情况下为文本选项卡初始化 OpenCC
        self.text_openCC = OpenCC('t2s') 
        # 文件选项卡将根据其自己的单选按钮初始化其 OpenCC 实例
        self.file_openCC = None # 稍后初始化

    def _create_text_conversion_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(4, weight=1) 

        self.text_mode_var = tk.StringVar(value="t2s") 
        radio_t2s = ctk.CTkRadioButton(controls_frame, text="繁体转简体", variable=self.text_mode_var, value="t2s", command=self._update_text_converter)
        radio_t2s.grid(row=0, column=0, padx=(10,5), pady=5, sticky="w")
        radio_s2t = ctk.CTkRadioButton(controls_frame, text="简体转繁体", variable=self.text_mode_var, value="s2t", command=self._update_text_converter)
        radio_s2t.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        convert_button = ctk.CTkButton(controls_frame, text="转换文本", command=self._convert_text_area_logic)
        convert_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        clear_button = ctk.CTkButton(controls_frame, text="清空", command=self._clear_text_area)
        clear_button.grid(row=0, column=3, padx=(5,10), pady=5, sticky="w")

        self.text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, height=15, undo=True)
        self.text_area.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        self._apply_theme_to_scrolledtext(self.text_area)

    def _create_file_conversion_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        # 根据需要配置行，例如用于输入、输出、控件、状态
        tab.grid_rowconfigure(3, weight=1) # 如果添加了状态或日志区域，则用于该区域

        # 文件转换模式
        mode_frame = ctk.CTkFrame(tab)
        mode_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        ctk.CTkLabel(mode_frame, text="转换模式:").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.file_mode_var = tk.StringVar(value="t2s")
        file_radio_t2s = ctk.CTkRadioButton(mode_frame, text="繁体转简体", variable=self.file_mode_var, value="t2s", command=self._update_file_converter)
        file_radio_t2s.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        file_radio_s2t = ctk.CTkRadioButton(mode_frame, text="简体转繁体", variable=self.file_mode_var, value="s2t", command=self._update_file_converter)
        file_radio_s2t.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self._update_file_converter() # 初始化 self.file_openCC

        # 输入文件选择
        input_file_frame = ctk.CTkFrame(tab)
        input_file_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        input_file_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(input_file_frame, text="选择输入文件:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.input_file_entry = ctk.CTkEntry(input_file_frame, placeholder_text='点击"浏览"选择文件')
        self.input_file_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky="ew")
        ctk.CTkButton(input_file_frame, text="浏览", width=80, command=self._browse_input_file).grid(row=0, column=2, padx=(0,10), pady=10)

        # 操作按钮
        ctk.CTkButton(tab, text="转换文件并另存为...", command=self._convert_file_logic).grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # 状态标签
        self.file_status_label = ctk.CTkLabel(tab, text="", text_color="gray") # 使用中性的默认颜色
        self.file_status_label.grid(row=3, column=0, padx=10, pady=(0,10), sticky="ewn")

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

    def _update_text_converter(self):
        mode = self.text_mode_var.get()
        self.text_openCC = OpenCC(mode) 

    def _update_file_converter(self):
        mode = self.file_mode_var.get()
        self.file_openCC = OpenCC(mode)

    def _convert_text_area_logic(self):
        original_text = self.text_area.get("1.0", tk.END).strip()
        if not original_text:
            messagebox.showinfo("提示", "请输入或粘贴需要转换的文本内容。")
            return
        
        try:
            converted_text = self.text_openCC.convert(original_text)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", converted_text)
        except Exception as e:
            messagebox.showerror("转换错误", f"文本转换过程中发生错误: {e}")

    def _clear_text_area(self):
        self.text_area.delete("1.0", tk.END)

    def _browse_input_file(self):
        file_path = filedialog.askopenfilename(
            title="选择待转换的文本文件",
            filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*"))
        )
        if file_path:
            self.input_file_entry.delete(0, tk.END)
            self.input_file_entry.insert(0, file_path)
            self.file_status_label.configure(text="")

    def _convert_file_logic(self):
        input_path = self.input_file_entry.get()
        if not input_path:
            messagebox.showerror("错误", "请先选择一个输入文件！")
            self.file_status_label.configure(text="错误: 请选择输入文件", text_color="red")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("错误", f"输入文件不存在: {input_path}")
            self.file_status_label.configure(text=f"错误: 输入文件不存在 {input_path}", text_color="red")
            return

        # 确定输出文件名建议
        path_parts = os.path.splitext(input_path)
        current_mode = self.file_mode_var.get()
        suffix = "_simplified" if current_mode == "t2s" else "_traditional"
        suggested_output_filename = f"{os.path.basename(path_parts[0])}{suffix}{path_parts[1]}"
        
        output_path = filedialog.asksaveasfilename(
            title="保存转换后的文件",
            initialfile=suggested_output_filename,
            defaultextension=path_parts[1],
            filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"),("All files", "*.*"))
        )

        if not output_path:
            self.file_status_label.configure(text="操作取消: 未选择保存路径", text_color="orange")
            return
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f_in, \
                 open(output_path, 'w', encoding='utf-8') as f_out:
                input_text = f_in.read()
                if self.file_openCC is None: # 应由 _update_file_converter 或在选项卡创建时初始化
                    self._update_file_converter()
                converted_text = self.file_openCC.convert(input_text)
                f_out.write(converted_text)
            
            success_message = f"文件已成功转换为 {current_mode} 并保存至:\\n{output_path}"
            self.file_status_label.configure(text=success_message, text_color="green")
            messagebox.showinfo("成功", success_message)
        except FileNotFoundError: # 应由先前的检查捕获，但作为安全措施
            message = f"错误: 输入文件未找到 {input_path}"
            self.file_status_label.configure(text=message, text_color="red")
            messagebox.showerror("文件错误", message)
        except Exception as e:
            message = f"文件转换失败: {e}"
            self.file_status_label.configure(text=message, text_color="red")
            messagebox.showerror("转换失败", message)

# 已移除 browse_input_file 和 convert_file 方法及相关的UI元素 (input_file_entry, status_label) 