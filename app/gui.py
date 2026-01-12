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
        self.geometry("600x520")
        self.minsize(500, 480)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Message queue for thread-safe GUI updates
        self.msg_queue = queue.Queue()

        # Store selected files
        self.orders_files = []
        self.custom_file = None

        # Build UI
        self._create_widgets()

        # Start queue checker
        self._check_queue()

    def _create_widgets(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Drop zones row expands

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Orders to Gangsheet",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 5))

        # Instructions
        instructions_text = (
            "How to use:\n"
            "1) Drop or browse for Shopify Orders CSV file(s)\n"
            "2) Optionally add a Custom CSV for personalised values\n"
            "3) Click Generate to create gang sheets"
        )
        instructions_label = ctk.CTkLabel(
            self,
            text=instructions_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        instructions_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10))

        # Orders CSV drop zone (left)
        self.orders_frame = ctk.CTkFrame(self, corner_radius=15)
        self.orders_frame.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="nsew")
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
        self.orders_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, 'orders'))
        self.orders_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, 'orders'))
        self.orders_frame.bind("<Button-1>", self._browse_orders)
        self.orders_label.bind("<Button-1>", self._browse_orders)

        # Custom CSV drop zone (right)
        self.custom_frame = ctk.CTkFrame(self, corner_radius=15)
        self.custom_frame.grid(row=2, column=1, padx=(10, 20), pady=10, sticky="nsew")
        self.custom_frame.grid_columnconfigure(0, weight=1)
        self.custom_frame.grid_rowconfigure(0, weight=1)

        self.custom_label = ctk.CTkLabel(
            self.custom_frame,
            text="Custom CSV\n(Optional)\n\nDrop or click",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.custom_label.grid(row=0, column=0, padx=20, pady=30)

        # Bind drag-and-drop for custom
        self.custom_frame.drop_target_register(DND_FILES)
        self.custom_frame.dnd_bind('<<Drop>>', self._on_drop_custom)
        self.custom_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, 'custom'))
        self.custom_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, 'custom'))
        self.custom_frame.bind("<Button-1>", self._browse_custom)
        self.custom_label.bind("<Button-1>", self._browse_custom)

        # Generate button
        self.generate_btn = ctk.CTkButton(
            self,
            text="Generate Gang Sheet",
            command=self._generate,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        self.generate_btn.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 5))

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Select an Orders CSV to get started",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 5))

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
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
        self.open_folder_btn.grid(row=6, column=0, columnspan=2, padx=20, pady=(0, 10))

        # Footer with licensing
        footer_label = ctk.CTkLabel(
            self,
            text="© 2026 Bootink. All rights reserved.",
            font=ctk.CTkFont(size=10),
            text_color="gray50"
        )
        footer_label.grid(row=7, column=0, columnspan=2, padx=20, pady=(5, 15))

    def _on_drag_enter(self, event, zone='orders'):
        """Visual feedback when dragging over."""
        if zone == 'orders':
            self.orders_frame.configure(border_width=3, border_color="#3B8ED0")
            self.orders_label.configure(text="Drop here!", text_color="#3B8ED0")
        else:
            self.custom_frame.configure(border_width=3, border_color="#3B8ED0")
            self.custom_label.configure(text="Drop here!", text_color="#3B8ED0")

    def _on_drag_leave(self, event, zone='orders'):
        """Reset visual state."""
        if zone == 'orders':
            self.orders_frame.configure(border_width=0)
            self._update_orders_label()
        else:
            self.custom_frame.configure(border_width=0)
            self._update_custom_label()

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

    def _update_custom_label(self):
        """Update custom label based on current selection."""
        if self.custom_file:
            filename = os.path.basename(self.custom_file)
            # Truncate long filenames
            if len(filename) > 20:
                filename = filename[:17] + "..."
            self.custom_label.configure(
                text=f"{filename}\n\nClick to change",
                text_color="green"
            )
        else:
            self.custom_label.configure(
                text="Custom CSV\n(Optional)\n\nDrop or click",
                text_color="gray"
            )

    def _on_drop_orders(self, event):
        """Handle dropped orders files."""
        self._on_drag_leave(event, 'orders')
        files = self._parse_drop_data(event.data)
        csv_files = [f for f in files if f.lower().endswith('.csv')]
        if csv_files:
            self.orders_files = csv_files
            self._update_orders_label()
            self._update_status()

    def _on_drop_custom(self, event):
        """Handle dropped custom file."""
        self._on_drag_leave(event, 'custom')
        files = self._parse_drop_data(event.data)
        csv_files = [f for f in files if f.lower().endswith('.csv')]
        if csv_files:
            self.custom_file = csv_files[0]  # Only use first file
            self._update_custom_label()
            self._update_status()

    def _update_status(self):
        """Update status based on current selections."""
        if self.orders_files:
            if self.custom_file:
                self.status_label.configure(
                    text="Ready to generate!",
                    text_color="orange"
                )
            else:
                self.status_label.configure(
                    text="Ready (custom values will use placeholders)",
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

    def _browse_custom(self, event=None):
        """Open file dialog to select custom CSV file."""
        from tkinter import filedialog
        file = filedialog.askopenfilename(
            title="Select Custom CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file:
            self.custom_file = file
            self._update_custom_label()
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

        # Run in background thread
        thread = threading.Thread(target=self._process_worker)
        thread.daemon = True
        thread.start()

    def _process_worker(self):
        """Worker thread for processing files."""
        total = len(self.orders_files)
        errors = []

        # Load custom lookup if custom file is provided
        custom_lookup = {}
        if self.custom_file:
            try:
                self.msg_queue.put(('status', "Loading custom values..."))
                custom_lookup = pipeline.load_custom_lookup(self.custom_file)
                self.msg_queue.put(('status', f"Loaded {len(custom_lookup)} custom values"))
            except Exception as e:
                self.msg_queue.put(('status', f"Warning: Could not load custom CSV: {e}"))

        for i, csv_path in enumerate(self.orders_files):
            try:
                filename = os.path.basename(csv_path)
                self.msg_queue.put(('status', f"Processing: {filename}"))

                # Process the CSV
                self._process_single_csv(csv_path, custom_lookup)

                self.msg_queue.put(('progress', (i + 1) / total))

            except Exception as e:
                errors.append(os.path.basename(csv_path))

        self.msg_queue.put(('done', errors))

    def _process_single_csv(self, csv_path, custom_lookup=None):
        """Process a single CSV file."""
        import pandas as pd
        from shapely import affinity
        from reportlab.lib.colors import CMYKColor
        from src import pdf_utils, layout

        # Reload flag lookup (in case paths changed)
        pipeline.FLAG_LOOKUP = pipeline._build_flag_lookup()

        # Setup paths - create subfolder for each order
        filename = os.path.basename(csv_path)
        order_name = filename.replace('.csv', '').replace('.CSV', '')
        order_folder = os.path.join(config.OUTPUT_DIR, order_name)
        os.makedirs(order_folder, exist_ok=True)

        output_path_with_border = os.path.join(order_folder, 'gangsheet.pdf')
        output_path_no_border = os.path.join(order_folder, 'gangsheet_no_border.pdf')

        # Load data
        df = pd.read_csv(csv_path)

        # Setup both PDFs
        c_with_border = pdf_utils.setup_canvas(output_path_with_border, (config.PAGE_WIDTH, config.PAGE_HEIGHT))
        c_no_border = pdf_utils.setup_canvas(output_path_no_border, (config.PAGE_WIDTH, config.PAGE_HEIGHT))

        # Collect items with custom lookup
        items = pipeline.collect_items_from_csv(df, custom_lookup)

        # Layout (use same layout for both)
        layout_mgr = layout.OptimizedLayoutManager(c_with_border)
        placed_items = layout_mgr.place_items(items)

        # Render all items to both PDFs, handling page breaks
        placed_items.sort(key=lambda p: p[2])  # Sort by page number
        current_page_with_border = 1
        current_page_no_border = 1
        for x, y, page, item in placed_items:
            # Handle page breaks for PDF with border
            while current_page_with_border < page:
                c_with_border.showPage()
                current_page_with_border += 1
            pipeline.render_item(c_with_border, x, y, item, draw_cutting_border=True)

            # Handle page breaks for PDF without border
            while current_page_no_border < page:
                c_no_border.showPage()
                current_page_no_border += 1
            pipeline.render_item(c_no_border, x, y, item, draw_cutting_border=False)

        # Save both PDFs
        c_with_border.save()
        c_no_border.save()

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
        # Re-enable generate button
        self.generate_btn.configure(state="normal")

        # Reset labels
        self._update_orders_label()
        self._update_custom_label()

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
