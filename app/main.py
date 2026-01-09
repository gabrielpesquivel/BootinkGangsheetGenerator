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
    Based on specs: <=3 chars = 1 square, >3 chars = 2 squares, >10 chars = 3 squares
    """
    char_count = len(text.strip())
    if char_count <= 3:
        return 1  # 25mm
    elif char_count <= 10:
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


def collect_items_from_csv(df):
    """
    First pass: collect all items from the CSV with their dimensions and render data.

    Returns:
        List of item dicts with 'width', 'height', 'type', and type-specific data
    """
    items = []

    for index, row in df.iterrows():
        lineitem_name = str(row.get('Lineitem name', ''))

        # Skip items we don't want to print
        if not lineitem_name or lineitem_name.strip() == '' or 'Priming Wipe' in lineitem_name:
            continue

        qty = int(row.get('Lineitem quantity', 1))

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

        if not text or text.strip() == '':
            continue

        # Determine size and geometry
        size = determine_size_category(text)
        size_cfg = config.SIZE_MAP.get(size, config.SIZE_MAP['Words'])
        grid_squares = determine_grid_squares(text)
        rect_width = grid_squares * config.GRID_SIZE
        rect_height = config.GRID_SIZE

        text_geo, bg_geo, w, h = geometry.create_sticker_geometry(
            text, config.FONT_PATH, size_cfg, rect_width, rect_height
        )

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


def render_item(c, x, y, item):
    """Render a single item at the given position."""
    w, h = item['width'], item['height']

    # Draw magenta cutting rectangle
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

        # Determine colors based on text color
        text_color = item.get('text_color', 'BLACK')
        if text_color == 'WHITE':
            # White text with black bubble fill at 3%
            text_cmyk = CMYKColor(0, 0, 0, 0)  # White
            bubble_cmyk = CMYKColor(0, 0, 0, 1)  # Black
        else:
            # Black text with white bubble fill at 3%
            text_cmyk = CMYKColor(0, 0, 0, 1)  # Black
            bubble_cmyk = CMYKColor(0, 0, 0, 0)  # White

        # Draw bubble (background) with 3% opacity, no stroke
        pdf_utils.draw_shapely_poly(c, final_bg, bubble_cmyk, alpha=0.03)
        # Draw text
        pdf_utils.draw_shapely_poly(c, final_text, text_cmyk, alpha=1.0)


def process_orders():
    # 1. Find CSV files
    input_files = [f for f in os.listdir(config.INPUT_DIR) if f.endswith('.csv')]

    if not input_files:
        print("No CSV files found in input_csv/")
        return

    for csv_file in input_files:
        print(f"Processing {csv_file}...")

        # Setup paths
        input_path = os.path.join(config.INPUT_DIR, csv_file)
        output_filename = csv_file.replace('.csv', '_gangsheet.pdf')
        output_path = os.path.join(config.OUTPUT_DIR, output_filename)

        # Load Data
        df = pd.read_csv(input_path)

        # Setup PDF
        c = pdf_utils.setup_canvas(output_path, (config.PAGE_WIDTH, config.PAGE_HEIGHT))

        # Phase 1: Collect all items
        items = collect_items_from_csv(df)
        print(f"  Collected {len(items)} items")

        # Count by size for stats
        small_count = sum(1 for i in items if i['width'] <= config.GRID_SIZE + 0.1)
        large_count = len(items) - small_count
        print(f"  Small items (1 square): {small_count}, Large items (2-3 squares): {large_count}")

        # Phase 2: Optimized layout
        layout_mgr = layout.OptimizedLayoutManager(c)
        placed_items = layout_mgr.place_items(items)

        # Phase 3: Render all items, handling page breaks
        # Sort by page number to render items in correct order
        placed_items.sort(key=lambda p: p[2])  # Sort by page number

        current_page = 1
        for x, y, page, item in placed_items:
            # Handle page breaks during rendering
            while current_page < page:
                c.showPage()
                current_page += 1
            render_item(c, x, y, item)

        # Save PDF
        c.save()
        print(f"  Pages: {layout_mgr.page_count}")
        print(f"  Saved: {output_path}")

if __name__ == "__main__":    
    if not os.path.exists(config.FONT_PATH):
        print(f"ERROR: Font not found at {config.FONT_PATH}")
        print("Please place a .ttf file in the assets folder.")
    else:
        process_orders()