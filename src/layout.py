from . import config

class LayoutManager:
    def __init__(self, canvas_obj):
        self.c = canvas_obj
        self.cursor_x = config.MARGIN
        self.cursor_y = config.PAGE_HEIGHT - config.MARGIN
        self.row_height = 0
        self.page_count = 1

    def add_item(self, width, height):
        """
        Calculates position for next item.
        Returns (x, y) or triggers new page if full.
        Rectangles touch edge-to-edge for maximum space utilization.
        """
        # Check if item fits in current row
        if self.cursor_x + width > config.PAGE_WIDTH - config.MARGIN:
            # Move to next row (no gap - rectangles touch)
            self.cursor_x = config.MARGIN
            self.cursor_y -= self.row_height
            self.row_height = 0

        # Check if item fits on page vertically
        if self.cursor_y - height < config.MARGIN:
            # New Page
            self.c.showPage()
            self.page_count += 1
            self.cursor_x = config.MARGIN
            self.cursor_y = config.PAGE_HEIGHT - config.MARGIN
            self.row_height = 0

        # Calculate draw position
        # cursor_y is the TOP of the row, so we draw down from there
        draw_x = self.cursor_x
        draw_y = self.cursor_y - height

        # Update cursor for next item (no gap - rectangles touch)
        self.cursor_x += width
        if height > self.row_height:
            self.row_height = height

        return draw_x, draw_y


class OptimizedLayoutManager:
    """
    Optimized layout manager that packs items efficiently.

    Strategy: First-Fit Decreasing with gap filling
    1. Collect all items first
    2. Sort by width (largest first)
    3. Place items row by row, filling gaps with smaller items
    """

    def __init__(self, canvas_obj):
        self.c = canvas_obj
        self.page_count = 1
        self.usable_width = config.PAGE_WIDTH - 2 * config.MARGIN
        self.usable_height = config.PAGE_HEIGHT - 2 * config.MARGIN

        # Track rows: list of (y_position, remaining_width, row_height, items)
        # items = list of (x, width) tuples for placed items
        self.rows = []
        self.current_page_y = config.PAGE_HEIGHT - config.MARGIN

    def _start_new_row(self, height):
        """Start a new row, handling page breaks."""
        if self.rows:
            # Move down by the height of the last row
            last_row = self.rows[-1]
            self.current_page_y = last_row['y'] - last_row['height']

        # Check if we need a new page
        if self.current_page_y - height < config.MARGIN:
            self.c.showPage()
            self.page_count += 1
            self.current_page_y = config.PAGE_HEIGHT - config.MARGIN
            # Clear rows for new page
            self.rows = []

        new_row = {
            'y': self.current_page_y,
            'remaining': self.usable_width,
            'height': height,
            'items': []
        }
        self.rows.append(new_row)
        return new_row

    def _find_gap_in_rows(self, width, height):
        """Find a gap in existing rows that can fit the item."""
        for row in self.rows:
            if row['remaining'] >= width and row['height'] >= height:
                return row
        return None

    def place_items(self, items):
        """
        Place all items optimally.

        Args:
            items: List of dicts with 'width', 'height', and 'render_fn'
                   render_fn(canvas, x, y) draws the item

        Returns:
            List of (x, y, item) tuples for all placed items
        """
        if not items:
            return []

        # Separate items by size: large (2-3 squares) vs small (1 square)
        small_items = []  # 1 grid square (25mm)
        large_items = []  # 2-3 grid squares (50mm, 75mm)

        for item in items:
            if item['width'] <= config.GRID_SIZE + 0.1:  # 1 square (with tolerance)
                small_items.append(item)
            else:
                large_items.append(item)

        # Sort large items by width descending (First-Fit Decreasing)
        large_items.sort(key=lambda x: x['width'], reverse=True)

        placed = []

        # Phase 1: Place large items, tracking gaps
        for item in large_items:
            w, h = item['width'], item['height']

            # Try to find existing row with space
            row = self._find_gap_in_rows(w, h)

            if row is None:
                # Need new row
                row = self._start_new_row(h)

            # Calculate x position (after existing items in row)
            x = config.MARGIN + (self.usable_width - row['remaining'])
            y = row['y'] - h

            # Update row tracking
            row['remaining'] -= w
            row['items'].append((x, w))

            placed.append((x, y, item))

        # Phase 2: Fill gaps with small items
        for item in small_items:
            w, h = item['width'], item['height']

            # Try to find existing row with space
            row = self._find_gap_in_rows(w, h)

            if row is None:
                # Need new row
                row = self._start_new_row(h)

            # Calculate x position
            x = config.MARGIN + (self.usable_width - row['remaining'])
            y = row['y'] - h

            # Update row tracking
            row['remaining'] -= w
            row['items'].append((x, w))

            placed.append((x, y, item))

        return placed