import os
import pandas as pd
from shapely import affinity
from reportlab.lib.colors import CMYKColor

from src import config, geometry, pdf_utils, layout
import re

# Regions that indicate a flag item
FLAG_REGIONS = ['Europe', 'Asia', 'Americas', 'Africa', 'Oceania', 'South America', 'Caribbean', 'Central America', 'Middle East', 'North America']

# Categories that indicate a symbol item (CSV name -> folder name)
SYMBOL_CATEGORY_MAP = {
    'Animals': 'animals',
    'Popular Symbols': 'popular',
    'Religious Icons': 'religious',
}

# Build a lookup of all available flags (lowercase country name -> full path)
def _build_flag_lookup():
    """Scan all flag subdirectories and build a lookup map."""
    lookup = {}
    if not os.path.exists(config.FLAGS_DIR):
        return lookup

    for subdir in os.listdir(config.FLAGS_DIR):
        subdir_path = os.path.join(config.FLAGS_DIR, subdir)
        if os.path.isdir(subdir_path):
            for filename in os.listdir(subdir_path):
                if filename.endswith('.svg'):
                    # Extract country name (without .svg), store as lowercase key
                    country_name = filename[:-4].lower()
                    lookup[country_name] = os.path.join(subdir_path, filename)
    return lookup

FLAG_LOOKUP = _build_flag_lookup()


# Build a lookup of all available symbols
# Key format: "category/name - color" or "category/name" for colorless files
def _build_symbol_lookup():
    """Scan all symbol subdirectories and build a lookup map."""
    lookup = {}
    symbols_dir = os.path.join(config.ASSETS_DIR, 'symbols')
    if not os.path.exists(symbols_dir):
        return lookup

    for subdir in os.listdir(symbols_dir):
        subdir_path = os.path.join(symbols_dir, subdir)
        if os.path.isdir(subdir_path):
            category = subdir.lower()
            for filename in os.listdir(subdir_path):
                if filename.endswith('.svg'):
                    # Extract symbol name (without .svg), store as lowercase
                    # e.g., "COBRA - WHITE.svg" -> "animals/cobra - white"
                    symbol_name = filename[:-4].lower()
                    lookup_key = f"{category}/{symbol_name}"
                    lookup[lookup_key] = os.path.join(subdir_path, filename)
    return lookup


SYMBOL_LOOKUP = _build_symbol_lookup()

# Patterns that indicate a custom item needing lookup
CUSTOM_PATTERNS = ['CUSTOM TEXT', 'CUSTOM INITIALS', 'CUSTOM NUMBERS', 'CUSTOM NAME', 'CUSTOM NUMBER', 'FIRST NAME', 'REQUEST A FLAG', 'PERIODS', 'SLASHES', 'LAST NAME', 'CUSTOM VERSE']


def safe_str(value):
    """Convert a pandas cell value to string, handling NaN as empty string."""
    if pd.isna(value):
        return ''
    return str(value).strip()


def load_custom_lookup(custom_csv_path):
    """
    Load the custom CSV and build a lookup dictionary.

    The custom CSV has rows where:
    - Lineitem row: Order #, Lineitem name = "Initials - CUSTOM INITIALS / BLACK"
    - Attribute row (following): Lineitem Attribute Key = "CUSTOM INITIALS", Value = "HÅ"

    Returns:
        Dict mapping (order_number, lineitem_name) -> custom_value
    """
    lookup = {}
    df = pd.read_csv(custom_csv_path)

    current_order = None
    current_lineitem = None

    for index, row in df.iterrows():
        order_num = safe_str(row.get('Name'))
        lineitem_name = safe_str(row.get('Lineitem name'))
        attr_key = safe_str(row.get('Lineitem Attribute Key'))
        attr_value = safe_str(row.get('Lineitem Attribute Value'))

        # Track current order (might be empty in continuation rows)
        if order_num:
            current_order = order_num

        # If this row has a lineitem name, track it
        if lineitem_name:
            current_lineitem = lineitem_name

        # If this row has attribute key/value, create the lookup entry
        if attr_key and attr_value and current_order and current_lineitem:
            lookup[(current_order, current_lineitem)] = attr_value

    return lookup


def is_custom_item(lineitem_name):
    """Check if lineitem name contains a custom placeholder pattern."""
    upper_name = lineitem_name.upper()
    return any(pattern in upper_name for pattern in CUSTOM_PATTERNS)


def get_custom_text(order_num, lineitem_name, custom_lookup):
    """
    Look up the actual custom text for a custom item.

    Returns the custom text if found, or None if not found.
    """
    if not custom_lookup:
        return None
    return custom_lookup.get((order_num, lineitem_name))


def get_symbol_path(lineitem_name):
    """
    Check if lineitem is a symbol item and return the symbol SVG path.

    Args:
        lineitem_name: The lineitem name (e.g., "Religious Icons - CHRISTIAN CROSS / Black")

    Returns:
        Path to symbol SVG file if it's a symbol item, None otherwise
    """
    # Check if it starts with a known symbol category
    for csv_category, folder_name in SYMBOL_CATEGORY_MAP.items():
        if lineitem_name.startswith(f'{csv_category} - '):
            # Extract symbol name and color
            rest = lineitem_name.split(' - ', 1)[1].strip()

            # Parse "SYMBOL_NAME / COLOR" format
            if ' / ' in rest:
                symbol_name, color = rest.split(' / ', 1)
                symbol_name = symbol_name.strip()
                color = color.strip().upper()
            else:
                symbol_name = rest
                color = None  # No color specified

            # Try with color first (e.g., "religious/christian cross - black")
            if color:
                symbol_key = f"{folder_name}/{symbol_name} - {color}".lower()
                symbol_path = SYMBOL_LOOKUP.get(symbol_key)
                if symbol_path and os.path.exists(symbol_path):
                    return symbol_path

            # Fall back to colorless file (e.g., "religious/ying and yang")
            symbol_key_no_color = f"{folder_name}/{symbol_name}".lower()
            symbol_path = SYMBOL_LOOKUP.get(symbol_key_no_color)
            if symbol_path and os.path.exists(symbol_path):
                return symbol_path

            print(f"Warning: Symbol file not found for '{symbol_name}' in category '{csv_category}'")
            return None
    return None


def get_flag_path(lineitem_name):
    """
    Check if lineitem is a flag item and return the flag SVG path.

    Args:
        lineitem_name: The lineitem name (e.g., "Europe - WALES")

    Returns:
        Path to flag SVG file if it's a flag item, None otherwise
    """
    # Check if it starts with a known region
    for region in FLAG_REGIONS:
        if lineitem_name.startswith(f'{region} - '):
            # Extract country name
            country = lineitem_name.split(' - ', 1)[1].strip().lower()
            # Remove any color suffix (e.g., "/ BLACK")
            if ' / ' in country:
                country = country.split(' / ')[0].strip()

            # Look up the flag file from our scanned lookup
            flag_path = FLAG_LOOKUP.get(country)

            if flag_path and os.path.exists(flag_path):
                return flag_path
            else:
                print(f"Warning: Flag file not found for '{country}'")
                return None
    return None


def determine_grid_squares(text):
    """
    Determine how many grid squares (25mm each) the rectangle should span.
    Based on specs: <=6 chars = 1 square, <=14 chars = 2 squares, >14 chars = 3 squares
    """
    char_count = len(text.strip())
    if char_count <= 6:
        return 1  # 25mm
    elif char_count <= 14:
        return 2  # 50mm
    else:
        return 3  # 75mm

def determine_size_category(text):
    """
    Determine size category based on text content according to asset_specs.md:
    - Flags: 6mm
    - Symbols: 10mm
    - Initials + Numbers: 5mm (1-2 characters)
    - Dates + Words over 3 characters: 4mm
    """
    text = text.strip()

    # Check for flag emojis (country flags are in range U+1F1E6-U+1F1FF)
    if any('\U0001F1E6' <= char <= '\U0001F1FF' for char in text):
        return 'Flags'

    # Check for symbols (single character that's not alphanumeric)
    if len(text) == 1 and not text.isalnum():
        return 'Symbols'

    # Check for initials or numbers (1-2 characters of letters/numbers)
    if len(text) <= 2 and text.replace(' ', '').isalnum():
        return 'Initials'

    # Everything else (dates, words over 3 characters)
    return 'Words'


def collect_items_from_csv(df, custom_lookup=None):
    """
    First pass: collect all items from the CSV with their dimensions and render data.

    Args:
        df: DataFrame from the orders CSV
        custom_lookup: Dict mapping (order_number, lineitem_name) -> custom_value

    Returns:
        List of item dicts with 'width', 'height', 'type', and type-specific data
    """
    items = []
    current_order = None

    for index, row in df.iterrows():
        lineitem_name = safe_str(row.get('Lineitem name'))

        # Track current order number (might be empty in continuation rows)
        order_num = safe_str(row.get('Name'))
        if order_num:
            current_order = order_num

        # Skip items we don't want to print
        if not lineitem_name or 'Priming Wipe' in lineitem_name:
            continue

        qty_val = row.get('Lineitem quantity')
        qty = 1 if pd.isna(qty_val) else int(qty_val)

        # Check if this is a flag item
        flag_path = get_flag_path(lineitem_name)
        if flag_path:
            flag_height_pts = config.SIZE_MAP['Flags']['target_height_mm'] * config.MM_TO_PTS

            for _ in range(qty):
                items.append({
                    'type': 'flag',
                    'width': config.GRID_SIZE,
                    'height': config.GRID_SIZE,
                    'flag_path': flag_path,
                    'flag_height_pts': flag_height_pts
                })
            continue

        # Check if this is a symbol item
        symbol_path = get_symbol_path(lineitem_name)
        if symbol_path:
            symbol_height_pts = config.SIZE_MAP['Symbols']['target_height_mm'] * config.MM_TO_PTS

            for _ in range(qty):
                items.append({
                    'type': 'symbol',
                    'width': config.GRID_SIZE,
                    'height': config.GRID_SIZE,
                    'symbol_path': symbol_path,
                    'symbol_height_pts': symbol_height_pts
                })
            continue

        # Extract text and color
        text_color = 'BLACK'  # Default
        if ' - ' in lineitem_name:
            text = lineitem_name.split(' - ', 1)[1]
            if ' / ' in text:
                parts = text.split(' / ')
                text = parts[0]
                if len(parts) > 1:
                    color_part = parts[1].strip().upper()
                    if color_part in ('BLACK', 'WHITE'):
                        text_color = color_part
        else:
            text = lineitem_name

        # Check if this is a custom item that needs lookup
        is_custom_flag = False
        if is_custom_item(lineitem_name) and current_order and custom_lookup:
            custom_text = get_custom_text(current_order, lineitem_name, custom_lookup)
            if custom_text:
                # For "REQUEST A FLAG" items, append " FLAG" to the custom value and use fluro yellow
                if 'REQUEST A FLAG' in lineitem_name.upper():
                    text = custom_text.upper() + " FLAG"
                    text_color = 'FLURO_YELLOW'
                    is_custom_flag = True
                else:
                    text = custom_text
            else:
                print(f"Warning: No custom value found for order {current_order}, item '{lineitem_name}'")

        if not text or text.strip() == '':
            continue

        # Determine size and geometry
        size = determine_size_category(text)
        size_cfg = config.SIZE_MAP.get(size, config.SIZE_MAP['Words'])

        # Custom flags always use 1 grid square with two-row layout
        if is_custom_flag:
            grid_squares = 1
        else:
            grid_squares = determine_grid_squares(text)
        rect_width = grid_squares * config.GRID_SIZE
        rect_height = config.GRID_SIZE

        try:
            if is_custom_flag:
                # Use two-row layout for custom flags
                text_geo, bg_geo, w, h = geometry.create_two_row_sticker_geometry(
                    text, config.FONT_PATH, size_cfg, rect_width, rect_height
                )
            else:
                text_geo, bg_geo, w, h = geometry.create_sticker_geometry(
                    text, config.FONT_PATH, size_cfg, rect_width, rect_height
                )
        except Exception as e:
            # Font doesn't support these characters - skip this item
            safe_text = text.encode('ascii', 'replace').decode('ascii')
            print(f"Warning: Could not render text '{safe_text}' - skipping item")
            continue

        for _ in range(qty):
            items.append({
                'type': 'sticker',
                'width': w,
                'height': h,
                'text_geo': text_geo,
                'bg_geo': bg_geo,
                'text_color': text_color
            })

    return items


def render_item(c, x, y, item, draw_cutting_border=True):
    """Render a single item at the given position."""
    w, h = item['width'], item['height']

    # Draw magenta cutting rectangle (optional)
    if draw_cutting_border:
        pdf_utils.draw_cutting_rectangle(c, x, y, w, h)

    if item['type'] == 'flag':
        # Get flag dimensions for centering
        svg_w, svg_h = pdf_utils.get_svg_dimensions(item['flag_path'], item['flag_height_pts'])
        center_x = x + (w - svg_w) / 2
        center_y = y + (h - svg_h) / 2
        pdf_utils.draw_svg(c, item['flag_path'], center_x, center_y, item['flag_height_pts'])

    elif item['type'] == 'symbol':
        # Get symbol dimensions for centering
        svg_w, svg_h = pdf_utils.get_svg_dimensions(item['symbol_path'], item['symbol_height_pts'])
        center_x = x + (w - svg_w) / 2
        center_y = y + (h - svg_h) / 2
        pdf_utils.draw_svg(c, item['symbol_path'], center_x, center_y, item['symbol_height_pts'])

    elif item['type'] == 'sticker':
        # Translate geometry to position
        final_text = affinity.translate(item['text_geo'], xoff=x, yoff=y)
        final_bg = affinity.translate(item['bg_geo'], xoff=x, yoff=y)

        # 0.6mm stroke width
        stroke_width_pts = 0.6

        # Determine colors based on text color
        text_color = item.get('text_color', 'BLACK')
        if text_color == 'WHITE':
            # White text with black bubble fill at 3%, black stroke
            text_cmyk = CMYKColor(0, 0, 0, 0)  # White
            bubble_cmyk = CMYKColor(0, 0, 0, 1)  # Black
            stroke_cmyk = CMYKColor(0, 0, 0, 1)  # Black stroke
        elif text_color == 'FLURO_YELLOW':
            # Fluorescent yellow text with white bubble fill at 3%
            text_cmyk = CMYKColor(0, 0, 1, 0)  # Yellow
            bubble_cmyk = CMYKColor(0, 0, 0, 0)  # White
            stroke_cmyk = None
        else:
            # Black text with white bubble fill at 3%
            text_cmyk = CMYKColor(0, 0, 0, 1)  # Black
            bubble_cmyk = CMYKColor(0, 0, 0, 0)  # White
            stroke_cmyk = None

        # Draw bubble (background) with 3% opacity, no stroke
        pdf_utils.draw_shapely_poly(c, final_bg, bubble_cmyk, alpha=0.03)
        # Draw text (with stroke for white text)
        if stroke_cmyk:
            pdf_utils.draw_shapely_poly(c, final_text, text_cmyk, alpha=1.0, stroke_color=stroke_cmyk, stroke_width=stroke_width_pts)
        else:
            pdf_utils.draw_shapely_poly(c, final_text, text_cmyk, alpha=1.0)


def process_orders():
    # 1. Find orders CSV files in orders/ subfolder
    if not os.path.exists(config.ORDERS_DIR):
        print(f"Orders directory not found: {config.ORDERS_DIR}")
        return

    input_files = [f for f in os.listdir(config.ORDERS_DIR) if f.endswith('.csv')]

    if not input_files:
        print("No CSV files found in input_csv/orders/")
        return

    # 2. Load custom lookup from custom/ subfolder
    custom_lookup = {}
    if os.path.exists(config.CUSTOM_DIR):
        custom_files = [f for f in os.listdir(config.CUSTOM_DIR) if f.endswith('.csv')]
        for custom_file in custom_files:
            custom_path = os.path.join(config.CUSTOM_DIR, custom_file)
            print(f"Loading custom values from {custom_file}...")
            file_lookup = load_custom_lookup(custom_path)
            custom_lookup.update(file_lookup)
            print(f"  Loaded {len(file_lookup)} custom values")

    if not custom_lookup:
        print("Warning: No custom CSV files found in input_csv/custom/ - custom items will use placeholder text")

    for csv_file in input_files:
        print(f"Processing {csv_file}...")

        # Setup paths
        input_path = os.path.join(config.ORDERS_DIR, csv_file)
        output_filename_with_border = csv_file.replace('.csv', '_gangsheet.pdf')
        output_filename_no_border = csv_file.replace('.csv', '_gangsheet_no_border.pdf')
        output_path_with_border = os.path.join(config.OUTPUT_DIR, output_filename_with_border)
        output_path_no_border = os.path.join(config.OUTPUT_DIR, output_filename_no_border)

        # Load Data
        df = pd.read_csv(input_path)

        # Setup both PDFs
        c_with_border = pdf_utils.setup_canvas(output_path_with_border, (config.PAGE_WIDTH, config.PAGE_HEIGHT))
        c_no_border = pdf_utils.setup_canvas(output_path_no_border, (config.PAGE_WIDTH, config.PAGE_HEIGHT))

        # Phase 1: Collect all items (with custom lookup)
        items = collect_items_from_csv(df, custom_lookup)
        print(f"  Collected {len(items)} items")

        # Count by size for stats
        small_count = sum(1 for i in items if i['width'] <= config.GRID_SIZE + 0.1)
        large_count = len(items) - small_count
        print(f"  Small items (1 square): {small_count}, Large items (2-3 squares): {large_count}")

        # Phase 2: Optimized layout (use same layout for both)
        layout_mgr = layout.OptimizedLayoutManager(c_with_border)
        placed_items = layout_mgr.place_items(items)

        # Phase 3: Render all items to both PDFs, handling page breaks
        # Sort by page number to render items in correct order
        placed_items.sort(key=lambda p: p[2])  # Sort by page number

        current_page_with_border = 1
        current_page_no_border = 1
        for x, y, page, item in placed_items:
            # Handle page breaks for PDF with border
            while current_page_with_border < page:
                c_with_border.showPage()
                current_page_with_border += 1
            render_item(c_with_border, x, y, item, draw_cutting_border=True)

            # Handle page breaks for PDF without border
            while current_page_no_border < page:
                c_no_border.showPage()
                current_page_no_border += 1
            render_item(c_no_border, x, y, item, draw_cutting_border=False)

        # Save both PDFs
        c_with_border.save()
        c_no_border.save()
        print(f"  Pages: {layout_mgr.page_count}")
        print(f"  Saved: {output_path_with_border}")
        print(f"  Saved: {output_path_no_border}")

if __name__ == "__main__":    
    if not os.path.exists(config.FONT_PATH):
        print(f"ERROR: Font not found at {config.FONT_PATH}")
        print("Please place a .ttf file in the assets folder.")
    else:
        process_orders()