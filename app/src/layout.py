from . import config


class OptimizedLayoutManager:
    """
    Layout manager for a single continuous sheet (580mm wide, variable height).

    Places items row by row, growing downward indefinitely.
    All items are on page 1 (no pagination).
    """

    def __init__(self):
        self.usable_width = config.PAGE_WIDTH - 2 * config.MARGIN
        self.rows = []
        self.current_y = config.PAGE_WIDTH  # placeholder, recalculated after layout
        # Will be set after place_items() based on actual PAGE_WIDTH at that time
        self._top = None

    def _start_new_row(self, height):
        """Start a new row below the last one."""
        if self.rows:
            last_row = self.rows[-1]
            self.current_y = last_row['y'] - last_row['height']
        else:
            self.current_y = self._top

        new_row = {
            'y': self.current_y,
            'remaining': self.usable_width,
            'height': height,
            'items': [],
        }
        self.rows.append(new_row)
        return new_row

    def place_items(self, items):
        """
        Place all items in order, row by row on a single page.

        Args:
            items: List of dicts with 'width', 'height', and type-specific data.

        Returns:
            List of (x, y, page, item) tuples for all placed items.
            page is always 1.
        """
        if not items:
            return []

        # We need a starting y that will be adjusted later when we know the
        # total height.  Use a large value so coordinates stay positive during
        # layout; they'll be translated when we know the final canvas height.
        # Actually, let's compute top from a large placeholder and then shift.
        # Simpler: lay out with top = MARGIN offset from a huge page, then
        # translate.  BUT the rendering code expects final coordinates, so
        # let's do two passes internally.

        # --- Pass 1: determine row structure (heights only) ---
        row_specs = []  # list of row_height values
        current_remaining = 0.0  # force first item to start a new row

        for item in items:
            w, h = item['width'], item['height']
            if current_remaining < w or not row_specs:
                row_specs.append(h)
                current_remaining = self.usable_width - w
            else:
                current_remaining -= w

        total_rows_height = sum(row_specs)
        total_height = total_rows_height + 2 * config.MARGIN
        if total_height < config.MIN_PAGE_HEIGHT:
            total_height = config.MIN_PAGE_HEIGHT

        self._total_height = total_height
        self._top = total_height - config.MARGIN

        # --- Pass 2: place items with correct y coordinates ---
        self.rows = []
        placed = []

        for item in items:
            w, h = item['width'], item['height']

            current_row = self.rows[-1] if self.rows else None
            if current_row is None or current_row['remaining'] < w:
                current_row = self._start_new_row(h)

            x = config.MARGIN + (self.usable_width - current_row['remaining'])
            y = current_row['y'] - h

            current_row['remaining'] -= w
            current_row['items'].append((x, w))

            placed.append((x, y, 1, item))

        return placed

    @property
    def total_height(self):
        """Total sheet height in points (available after place_items)."""
        return getattr(self, '_total_height', config.MIN_PAGE_HEIGHT)
