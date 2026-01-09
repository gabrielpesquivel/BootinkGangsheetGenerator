"""
Shopify Orders Pipeline - GUI Application
Drag and drop CSV files to generate gang sheets.
"""
import os
import sys
import threading
import queue
from pathlib import Path

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

# Handle PyInstaller bundled app paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # For output, use the directory where the exe is located
    EXE_DIR = os.path.dirname(sys.executable)
else:
    # Running from source: go up from app/ to root/
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(APP_DIR)
    EXE_DIR = BASE_DIR

# Override config paths for bundled app
import src.config as config
config.BASE_DIR = BASE_DIR
config.ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
config.FONT_PATH = os.path.join(config.ASSETS_DIR, 'fonts', 'Industry_Ultra.ttf')
config.FLAGS_DIR = os.path.join(config.ASSETS_DIR, 'flags')
config.OUTPUT_DIR = os.path.join(EXE_DIR, 'output_sheet')

# Ensure output directory exists
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

# Now import main module (after config is set)
import main as pipeline


class TkinterDnDCustomTk(ctk.CTk, TkinterDnD.DnDWrapper):
    """Custom CTk class with drag-and-drop support."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class App(TkinterDnDCustomTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Shopify Gang Sheet Generator")
        self.geometry("500x380")
        self.minsize(400, 320)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Message queue for thread-safe GUI updates
        self.msg_queue = queue.Queue()

        # Build UI
        self._create_widgets()

        # Start queue checker
        self._check_queue()

    def _create_widgets(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Gang Sheet Generator",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Drop zone frame
        self.drop_frame = ctk.CTkFrame(self, corner_radius=15)
        self.drop_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_frame.grid_rowconfigure(0, weight=1)

        # Drop zone label
        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="Drag & Drop CSV Files Here\n\nor click to browse",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.drop_label.grid(row=0, column=0, padx=40, pady=40)

        # Bind drag-and-drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)
        self.drop_frame.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.drop_frame.dnd_bind('<<DragLeave>>', self._on_drag_leave)

        # Click to browse
        self.drop_frame.bind("<Button-1>", self._browse_files)
        self.drop_label.bind("<Button-1>", self._browse_files)

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 5))

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress.set(0)

        # Open folder button
        self.open_folder_btn = ctk.CTkButton(
            self,
            text="Open Output Folder",
            command=self._open_output_folder
        )
        self.open_folder_btn.grid(row=4, column=0, padx=20, pady=(0, 20))

    def _on_drag_enter(self, event):
        """Visual feedback when dragging over."""
        self.drop_frame.configure(border_width=3, border_color="#3B8ED0")
        self.drop_label.configure(text="Drop files here!", text_color="#3B8ED0")

    def _on_drag_leave(self, event):
        """Reset visual state."""
        self.drop_frame.configure(border_width=0)
        self.drop_label.configure(
            text="Drag & Drop CSV Files Here\n\nor click to browse",
            text_color="gray"
        )

    def _on_drop(self, event):
        """Handle dropped files."""
        self._on_drag_leave(event)  # Reset visual state

        # Parse dropped file paths (handles spaces in filenames)
        files = self._parse_drop_data(event.data)
        csv_files = [f for f in files if f.lower().endswith('.csv')]

        if not csv_files:
            self._log("No CSV files found in dropped items.")
            return

        self._process_files(csv_files)

    def _parse_drop_data(self, data):
        """Parse the dropped data string into file paths."""
        files = []
        # Windows wraps paths with spaces in curly braces
        if '{' in data:
            import re
            # Match both {path with spaces} and regular paths
            pattern = r'\{([^}]+)\}|(\S+)'
            matches = re.findall(pattern, data)
            for match in matches:
                path = match[0] or match[1]
                if path:
                    files.append(path)
        else:
            files = data.split()
        return files

    def _browse_files(self, event=None):
        """Open file dialog to select CSV files."""
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if files:
            self._process_files(list(files))

    def _process_files(self, file_paths):
        """Process CSV files in a background thread."""
        self.progress.set(0)
        self.status_label.configure(text=f"Processing {len(file_paths)} file(s)...", text_color="orange")

        # Disable drop zone during processing
        self.drop_label.configure(text="Processing...", text_color="orange")

        # Run in background thread
        thread = threading.Thread(target=self._process_worker, args=(file_paths,))
        thread.daemon = True
        thread.start()

    def _process_worker(self, file_paths):
        """Worker thread for processing files."""
        total = len(file_paths)
        errors = []

        for i, csv_path in enumerate(file_paths):
            try:
                filename = os.path.basename(csv_path)
                self.msg_queue.put(('status', f"Processing: {filename}"))

                # Process the CSV
                self._process_single_csv(csv_path)

                self.msg_queue.put(('progress', (i + 1) / total))

            except Exception as e:
                errors.append(os.path.basename(csv_path))

        self.msg_queue.put(('done', errors))

    def _process_single_csv(self, csv_path):
        """Process a single CSV file."""
        import pandas as pd
        from shapely import affinity
        from reportlab.lib.colors import CMYKColor
        from src import pdf_utils, layout

        # Reload flag lookup (in case paths changed)
        pipeline.FLAG_LOOKUP = pipeline._build_flag_lookup()

        # Setup paths
        filename = os.path.basename(csv_path)
        output_filename = filename.replace('.csv', '_gangsheet.pdf')
        output_path = os.path.join(config.OUTPUT_DIR, output_filename)

        # Load data
        df = pd.read_csv(csv_path)

        # Setup PDF
        c = pdf_utils.setup_canvas(output_path, (config.PAGE_WIDTH, config.PAGE_HEIGHT))

        # Collect items
        items = pipeline.collect_items_from_csv(df)

        # Layout
        layout_mgr = layout.OptimizedLayoutManager(c)
        placed_items = layout_mgr.place_items(items)

        # Render all items, handling page breaks
        placed_items.sort(key=lambda p: p[2])  # Sort by page number
        current_page = 1
        for x, y, page, item in placed_items:
            while current_page < page:
                c.showPage()
                current_page += 1
            pipeline.render_item(c, x, y, item)

        # Save
        c.save()

    def _check_queue(self):
        """Check message queue for updates from worker thread."""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()

                if msg_type == 'status':
                    self.status_label.configure(text=data, text_color="orange")
                elif msg_type == 'progress':
                    self.progress.set(data)
                elif msg_type == 'done':
                    self._on_processing_done(data)

        except queue.Empty:
            pass

        # Check again after 100ms
        self.after(100, self._check_queue)

    def _on_processing_done(self, errors):
        """Called when all processing is complete."""
        self.drop_label.configure(
            text="Drag & Drop CSV Files Here\n\nor click to browse",
            text_color="gray"
        )
        self.progress.set(1)

        if errors:
            self.status_label.configure(text=f"Done with {len(errors)} error(s)", text_color="red")
        else:
            self.status_label.configure(text="Ready!", text_color="green")

    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        output_dir = config.OUTPUT_DIR
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':
            os.system(f'open "{output_dir}"')
        else:
            os.system(f'xdg-open "{output_dir}"')


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
