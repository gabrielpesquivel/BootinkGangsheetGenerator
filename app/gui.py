"""
Shopify Orders Pipeline - GUI Application
Drag and drop CSV files to generate gang sheets.
"""
import os
import shutil
import sys
import threading
import queue
from pathlib import Path

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

# Handle PyInstaller bundled app paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # For output, use the user's Downloads folder
    DOWNLOADS_DIR = os.path.join(os.path.expanduser('~'), 'Downloads')
else:
    # Running from source: go up from app/ to root/
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(APP_DIR)
    DOWNLOADS_DIR = os.path.join(os.path.expanduser('~'), 'Downloads')

# Override config paths for bundled app
import src.config as config
config.BASE_DIR = BASE_DIR
config.ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
config.FONT_PATH = os.path.join(config.ASSETS_DIR, 'fonts', 'Industry_Ultra.ttf')
config.FLAGS_DIR = os.path.join(config.ASSETS_DIR, 'flags')
config.OUTPUT_DIR = os.path.join(DOWNLOADS_DIR, 'GangSheets')

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
        self.geometry("500x480")
        self.minsize(400, 420)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Message queue for thread-safe GUI updates
        self.msg_queue = queue.Queue()

        # Store selected files
        self.orders_files = []

        # Build UI
        self._create_widgets()

        # Start queue checker
        self._check_queue()

    def _create_widgets(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Drop zone row expands

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Orders to Gangsheet",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Separator line
        separator = ctk.CTkFrame(self, height=2, fg_color="gray30")
        separator.grid(row=1, column=0, padx=40, pady=(0, 10), sticky="ew")

        # Instructions
        instructions_text = (
            "How to use:\n"
            "1) Drop or browse for Shopify Orders CSV file(s)\n"
            "2) Click Generate to create gang sheets"
        )
        instructions_label = ctk.CTkLabel(
            self,
            text=instructions_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        instructions_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # Orders CSV drop zone (full width)
        self.orders_frame = ctk.CTkFrame(self, corner_radius=15)
        self.orders_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.orders_frame.grid_columnconfigure(0, weight=1)
        self.orders_frame.grid_rowconfigure(0, weight=1)

        self.orders_label = ctk.CTkLabel(
            self.orders_frame,
            text="Orders CSV\n\nDrop or click",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.orders_label.grid(row=0, column=0, padx=20, pady=30)

        # Bind drag-and-drop for orders
        self.orders_frame.drop_target_register(DND_FILES)
        self.orders_frame.dnd_bind('<<Drop>>', self._on_drop_orders)
        self.orders_frame.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.orders_frame.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        self.orders_frame.bind("<Button-1>", self._browse_orders)
        self.orders_label.bind("<Button-1>", self._browse_orders)

        # Generate button
        self.generate_btn = ctk.CTkButton(
            self,
            text="Generate Gang Sheet",
            command=self._generate,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        self.generate_btn.grid(row=4, column=0, padx=20, pady=(10, 5))

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Select an Orders CSV to get started",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=5, column=0, padx=20, pady=(0, 5))

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress.set(0)

        # Open folder button
        self.open_folder_btn = ctk.CTkButton(
            self,
            text="Open Output Folder",
            command=self._open_output_folder,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90")
        )
        self.open_folder_btn.grid(row=7, column=0, padx=20, pady=(0, 10))

        # Footer with licensing
        footer_label = ctk.CTkLabel(
            self,
            text="\u00a9 2026 Bootink. All rights reserved.",
            font=ctk.CTkFont(size=10),
            text_color="gray50"
        )
        footer_label.grid(row=8, column=0, padx=20, pady=(5, 15))

    def _on_drag_enter(self, event):
        """Visual feedback when dragging over."""
        self.orders_frame.configure(border_width=3, border_color="#3B8ED0")
        self.orders_label.configure(text="Drop here!", text_color="#3B8ED0")

    def _on_drag_leave(self, event):
        """Reset visual state."""
        self.orders_frame.configure(border_width=0)
        self._update_orders_label()

    def _update_orders_label(self):
        """Update orders label based on current selection."""
        if self.orders_files:
            count = len(self.orders_files)
            self.orders_label.configure(
                text=f"{count} file(s) selected\n\nClick to change",
                text_color="green"
            )
        else:
            self.orders_label.configure(
                text="Orders CSV\n\nDrop or click",
                text_color="gray"
            )

    def _on_drop_orders(self, event):
        """Handle dropped orders files."""
        self._on_drag_leave(event)
        files = self._parse_drop_data(event.data)
        csv_files = [f for f in files if f.lower().endswith('.csv')]
        if csv_files:
            self.orders_files = csv_files
            self._update_orders_label()
            self._update_status()

    def _update_status(self):
        """Update status based on current selections."""
        if self.orders_files:
            self.status_label.configure(
                text="Ready to generate!",
                text_color="orange"
            )
        else:
            self.status_label.configure(
                text="Select an Orders CSV to get started",
                text_color="gray"
            )

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

    def _browse_orders(self, event=None):
        """Open file dialog to select orders CSV files."""
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title="Select Orders CSV Files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if files:
            self.orders_files = list(files)
            self._update_orders_label()
            self._update_status()

    def _generate(self):
        """Start generation process."""
        if not self.orders_files:
            self.status_label.configure(text="Please select an Orders CSV first", text_color="red")
            return

        self.progress.set(0)
        self.status_label.configure(text=f"Processing {len(self.orders_files)} file(s)...", text_color="orange")

        # Disable buttons during processing
        self.generate_btn.configure(state="disabled")
        self.orders_label.configure(text="Processing...", text_color="orange")

        # Start simulated progress animation
        self._simulated_progress = 0
        self._processing = True
        self._animate_progress()

        # Run in background thread
        thread = threading.Thread(target=self._process_worker)
        thread.daemon = True
        thread.start()

    def _process_worker(self):
        """Worker thread for processing files."""
        total = len(self.orders_files)
        errors = []

        for i, csv_path in enumerate(self.orders_files):
            try:
                filename = os.path.basename(csv_path)
                self.msg_queue.put(('status', f"Processing: {filename}"))

                # Process the CSV (custom values are inline in the unified format)
                self._process_single_csv(csv_path)

                self.msg_queue.put(('progress', (i + 1) / total))

            except Exception as e:
                errors.append(os.path.basename(csv_path))

        self.msg_queue.put(('done', errors))

    def _process_single_csv(self, csv_path):
        """Process a single CSV file."""
        import pandas as pd
        from src import pdf_utils, layout

        # Reload flag lookup (in case paths changed)
        pipeline.FLAG_LOOKUP = pipeline._build_flag_lookup()

        # Setup paths - create subfolder for each order
        filename = os.path.basename(csv_path)
        order_name = filename.replace('.csv', '').replace('.CSV', '')
        order_folder = os.path.join(config.OUTPUT_DIR, order_name)
        os.makedirs(order_folder, exist_ok=True)

        output_path = os.path.join(order_folder, 'gangsheet.pdf')

        # Load data (utf-8-sig preserves accented characters)
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # Collect items (custom values are inline in properties)
        items = pipeline.collect_items_from_csv(df)

        # Layout to determine total height
        layout_mgr = layout.OptimizedLayoutManager()
        placed_items = layout_mgr.place_items(items)
        sheet_height = layout_mgr.total_height

        # Create canvas with dynamic height and render
        c = pdf_utils.setup_canvas(output_path, (config.PAGE_WIDTH, sheet_height))

        for x, y, page, item in placed_items:
            pipeline.render_item(c, x, y, item, draw_cutting_border=True)

        # Save PDF
        c.save()

        # Save .ai copy (Illustrator opens PDF-based .ai files natively)
        ai_path = output_path.replace('.pdf', '.ai')
        shutil.copy2(output_path, ai_path)

    def _animate_progress(self):
        """Animate the progress bar slowly while processing."""
        if not self._processing:
            return

        # Slowly increment progress (max 90% to leave room for completion)
        if self._simulated_progress < 0.9:
            self._simulated_progress += 0.02
            self.progress.set(self._simulated_progress)

        # Continue animating every 200ms
        self.after(200, self._animate_progress)

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
        # Stop progress animation
        self._processing = False

        # Re-enable generate button
        self.generate_btn.configure(state="normal")

        # Reset labels
        self._update_orders_label()

        self.progress.set(1)

        if errors:
            self.status_label.configure(text=f"Done with {len(errors)} error(s)", text_color="red")
        else:
            self.status_label.configure(text="Done! Gang sheets saved.", text_color="green")

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
