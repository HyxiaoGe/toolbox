import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os

# Imports for tool frames
from gui_app.tool_trad_to_simple import TraditionalToSimplifiedFrame
from gui_app.tool_file_clean import FileCleanFrame
from gui_app.tool_batch_rename import BatchRenameFrame
from gui_app.tool_video_duration import VideoDurationFrame
from gui_app.tool_find_duplicates import FindDuplicatesFrame
from gui_app.tool_software_quickstart import SoftwareQuickstartFrame

# --- UI Frames for each tool ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("工具箱应用")
        self.geometry("900x700")
        ctk.set_appearance_mode("System") 
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.nav_panel = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.nav_panel.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)
        self.nav_panel.grid_rowconfigure(6, weight=1) # Adjust row index based on number of buttons + label

        ctk.CTkLabel(self.nav_panel, text="工具选择", font=ctk.CTkFont(size=15, weight="bold"))\
            .grid(row=0, column=0, padx=20, pady=(20, 10))

        self.buttons = {}
        tool_names = [
            "文本繁简转换", "文件名清理", "批量文件重命名", 
            "视频时长统计", "查找重复文件", "软件快捷启动"
        ]
        for i, name in enumerate(tool_names):
            button = ctk.CTkButton(self.nav_panel, text=name, command=lambda n=name: self.select_frame_by_name(n))
            button.grid(row=i+1, column=0, padx=20, pady=10, sticky="ew")
            self.buttons[name] = button

        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)

        # Initialize frames for each tool
        self.frames = {}
        self.frames["文本繁简转换"] = TraditionalToSimplifiedFrame(self.right_panel)
        self.frames["文件名清理"] = FileCleanFrame(self.right_panel)
        self.frames["批量文件重命名"] = BatchRenameFrame(self.right_panel)
        self.frames["视频时长统计"] = VideoDurationFrame(self.right_panel)
        self.frames["查找重复文件"] = FindDuplicatesFrame(self.right_panel)
        self.frames["软件快捷启动"] = SoftwareQuickstartFrame(self.right_panel)
        
        # Grid all frames once, they will be raised by select_frame_by_name
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.select_frame_by_name(tool_names[0]) # Select initial frame (first in list)

    def select_frame_by_name(self, name):
        # Deselect all buttons (visually)
        for btn_name, button_widget in self.buttons.items():
            # Assuming default button color for deselected, and theme color for selected
            # This might need adjustment based on how CTkButton handles colors
            is_selected = (btn_name == name)
            current_fg_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            current_hover_color = button_widget._hover_color # CTkButton specific
            
            if isinstance(current_fg_color, (list, tuple)):
                # If theme color is a light/dark tuple, pick based on current mode
                effective_fg_color = current_fg_color[1] if ctk.get_appearance_mode().lower() == "dark" else current_fg_color[0]
            else:
                effective_fg_color = current_fg_color

            button_widget.configure(fg_color=effective_fg_color if is_selected else current_hover_color if button_widget._hover else "transparent") # A bit simplified

        # Raise the selected frame
        if name in self.frames:
            self.frames[name].tkraise()
        else:
            print(f"Error: No frame configured for '{name}'")


if __name__ == "__main__":
    app = App()
    app.mainloop() 