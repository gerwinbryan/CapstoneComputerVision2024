import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os


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

        # Input Type Frame
        input_frame = ttk.LabelFrame(self.root, text="Select Input Type")
        input_frame.pack(padx=10, pady=5, fill="x")

        ttk.Radiobutton(input_frame, text="Video File", value="video",
                        variable=self.input_type).pack(side="left", padx=5)
        ttk.Radiobutton(input_frame, text="RTSP Stream", value="rtsp",
                        variable=self.input_type).pack(side="left", padx=5)
        ttk.Radiobutton(input_frame, text="RTMP Stream", value="rtmp",
                        variable=self.input_type).pack(side="left", padx=5)

        # Path Entry Frame
        path_frame = ttk.LabelFrame(self.root, text="Enter Path")
        path_frame.pack(padx=10, pady=5, fill="x")

        self.path_entry = ttk.Entry(path_frame, textvariable=self.input_path)
        self.path_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.browse_btn = ttk.Button(path_frame, text="Browse", command=self.browse_file)
        self.browse_btn.pack(side="right", padx=5)

        # Example Label
        example_frame = ttk.LabelFrame(self.root, text="Example Format")
        example_frame.pack(padx=10, pady=5, fill="x")

        self.example_label = ttk.Label(example_frame, text="Select input type to see example")
        self.example_label.pack(padx=5, pady=5)

        # Update example when input type changes
        self.input_type.trace('w', self.update_example)

        # Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="OK", command=self.ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side="left", padx=5)

    def update_example(self, *args):
        examples = {
            "video": "path/to/video.mp4",
            "rtsp": "rtsp://username:password@ip:port/path",
            "rtmp": "rtmp://server:port/app/stream-key"
        }
        self.example_label.config(text=examples.get(self.input_type.get(), ""))
        self.browse_btn.config(state="normal" if self.input_type.get() == "video" else "disabled")

    def ok(self):
        input_path = self.input_path.get()
        if not input_path:
            messagebox.showerror("Error", "Please enter a path")
            return

        try:
            if self.input_type.get() == "video":
                if not os.path.exists(input_path):
                    messagebox.showerror("Error", "Video file does not exist")
                    return

            # Try to open the video source
            self.cap = cv2.VideoCapture(input_path)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Could not open video source")
                return

            self.setup_complete = True
            self.root.quit()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open video source: {str(e)}")
            return

    def browse_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")])
        if filename:
            self.input_path.set(filename)

    def cancel(self):
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