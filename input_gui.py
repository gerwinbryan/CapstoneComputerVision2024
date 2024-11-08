import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2


class InputConfigGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Input Configuration")
        self.root.geometry("400x200")

        # Variables
        self.input_type = tk.StringVar(value="video")
        self.input_path = tk.StringVar()
        self.setup_complete = False
        self.cap = None

        # Input Type Selection
        frame_type = ttk.LabelFrame(self.root, text="Input Type", padding="5")
        frame_type.pack(fill="x", padx=5, pady=5)

        ttk.Radiobutton(frame_type, text="Video File", variable=self.input_type,
                        value="video", command=self.toggle_input).pack(side="left", padx=5)
        ttk.Radiobutton(frame_type, text="RTSP Stream", variable=self.input_type,
                        value="rtsp", command=self.toggle_input).pack(side="left", padx=5)

        # Path Input
        frame_path = ttk.Frame(self.root, padding="5")
        frame_path.pack(fill="x", padx=5, pady=5)

        self.path_entry = ttk.Entry(frame_path, textvariable=self.input_path)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.browse_button = ttk.Button(frame_path, text="Browse", command=self.browse_file)
        self.browse_button.pack(side="right")

        # Start Button
        self.start_button = ttk.Button(self.root, text="Start", command=self.validate_and_start)
        self.start_button.pack(pady=20)

    def toggle_input(self):
        if self.input_type.get() == "video":
            self.browse_button["state"] = "normal"
            self.path_entry.delete(0, tk.END)
        else:
            self.browse_button["state"] = "disabled"
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, "rtsp://")

    def browse_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")])
        if filename:
            self.input_path.set(filename)

    def validate_and_start(self):
        path = self.input_path.get()
        if not path:
            messagebox.showerror("Error", "Please enter a path")
            return

        # Try to open the video source
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open video source")
            return

        self.setup_complete = True
        self.root.quit()

    def run(self):
        self.root.mainloop()
        self.root.destroy()
        return self.setup_complete, self.input_path.get(), self.cap


def confirm_region_selection():
    """Show a messagebox asking whether to use existing region"""
    return messagebox.askyesno(
        "Region Selection",
        "An existing region configuration was found. Would you like to use it?",
        icon='question'
    )