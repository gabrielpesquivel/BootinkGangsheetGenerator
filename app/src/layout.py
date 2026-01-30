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
            # Don't call showPage() here - just track the page break
            # The rendering loop will handle page changes
            self.page_count += 1
            self.current_page_y = config.PAGE_HEIGHT - config.MARGIN
            # Clear rows for new page
            self.rows = []

        new_row = {
            'y': self.current_page_y,
            'remaining': self.usable_width,
            'height': height,
            'items': [],
            'page': self.page_count  # Track which page this row belongs to
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
        Place all items in order (no optimization/reordering).

        Args:
            items: List of dicts with 'width', 'height', and 'render_fn'
                   render_fn(canvas, x, y) draws the item

        Returns:
            List of (x, y, page, item) tuples for all placed items
        """
        if not items:
            return []

        placed = []

        # Place items in order, row by row
        for item in items:
            w, h = item['width'], item['height']

            # Check if item fits in current row
            current_row = self.rows[-1] if self.rows else None

            if current_row is None or current_row['remaining'] < w:
                # Need new row
                current_row = self._start_new_row(h)

            # Calculate x position (after existing items in row)
            x = config.MARGIN + (self.usable_width - current_row['remaining'])
            y = current_row['y'] - h

            # Update row tracking
            current_row['remaining'] -= w
            current_row['items'].append((x, w))

            placed.append((x, y, current_row['page'], item))

        return placed