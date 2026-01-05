import os
import pandas as pd
from shapely import affinity
from reportlab.lib.colors import CMYKColor

from src import config, geometry, pdf_utils, layout
import re

# Regions that indicate a flag item
FLAG_REGIONS = ['Europe', 'Asia', 'Americas', 'Africa', 'Oceania']

# Map country names to flag file names (lowercase, .svg extension)
# For testing: map countries to 'australia' since that's the only flag available
FLAG_FILE_MAP = {
    'australia': 'australia',
    'wales': 'australia',      # Mapped to Australia for testing
    'bosnia': 'australia',     # Mapped to Australia for testing
    'pakistan': 'australia',   # Mapped to Australia for testing
    'slovenia': 'australia',   # Mapped to Australia for testing
    'portugal': 'australia',   # Mapped to Australia for testing
}

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

            # Look up the flag file
            flag_file = FLAG_FILE_MAP.get(country, country)
            flag_path = os.path.join(config.FLAGS_DIR, f'{flag_file}.svg')

            if os.path.exists(flag_path):
                return flag_path
            else:
                print(f"Warning: Flag file not found for '{country}': {flag_path}")
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
        layout_mgr = layout.LayoutManager(c)

        # Process Rows
        for index, row in df.iterrows():
            # Parse the lineitem name (format: "Category - TEXT / COLOR")
            lineitem_name = str(row.get('Lineitem name', ''))

            # Skip items we don't want to print (like Priming Wipe)
            if not lineitem_name or lineitem_name.strip() == '' or 'Priming Wipe' in lineitem_name:
                continue

            qty = int(row.get('Lineitem quantity', 1))

            # Check if this is a flag item
            flag_path = get_flag_path(lineitem_name)
            if flag_path:
                # Handle flag items - render SVG at 6mm height
                flag_height_pts = config.SIZE_MAP['Flags']['target_height_mm'] * config.MM_TO_PTS

                # Add to sheet for each quantity
                for _ in range(qty):
                    # Use 1 grid square for flags (25mm width)
                    w = config.GRID_SIZE
                    h = config.GRID_SIZE

                    # Get Position
                    x, y = layout_mgr.add_item(w, h)

                    # Draw magenta cutting rectangle
                    pdf_utils.draw_cutting_rectangle(c, x, y, w, h)

                    # Get flag dimensions to calculate centered position
                    svg_w, svg_h = pdf_utils.get_svg_dimensions(flag_path, flag_height_pts)

                    # Calculate centered position within the grid square
                    center_x = x + (w - svg_w) / 2
                    center_y = y + (h - svg_h) / 2

                    # Draw the flag SVG centered in the cell
                    pdf_utils.draw_svg(c, flag_path, center_x, center_y, flag_height_pts)

                continue  # Skip the text rendering below

            # Extract the text part (between the dash and slash, or the whole name if no slash)
            if ' - ' in lineitem_name:
                text = lineitem_name.split(' - ', 1)[1]  # Get everything after first " - "
                if ' / ' in text:
                    text = text.split(' / ')[0]  # Get everything before " / "
            else:
                text = lineitem_name

            # Skip empty text
            if not text or text.strip() == '':
                continue

            # Determine size category based on text content
            size = determine_size_category(text)

            # Get Config for this size
            size_cfg = config.SIZE_MAP.get(size, config.SIZE_MAP['Words'])

            # Determine rectangle dimensions based on character count
            grid_squares = determine_grid_squares(text)
            rect_width = grid_squares * config.GRID_SIZE
            rect_height = config.GRID_SIZE  # Height is always 1 grid square (25mm)

            # Generate Geometry (Once per unique design)
            # Text will be centered within the rectangle
            text_geo, bg_geo, w, h = geometry.create_sticker_geometry(
                text, config.FONT_PATH, size_cfg, rect_width, rect_height
            )

            # Add to Sheet (Repeat for Quantity)
            for _ in range(qty):
                # Get Position
                x, y = layout_mgr.add_item(w, h)

                # Draw magenta cutting rectangle
                pdf_utils.draw_cutting_rectangle(c, x, y, w, h)

                # Move Geometry to Position
                final_text = affinity.translate(text_geo, xoff=x, yoff=y)
                final_bg = affinity.translate(bg_geo, xoff=x, yoff=y)

                # Draw Background (White 3% opacity) - 0.5mm offset outline for peeling bubble
                # CMYK(0,0,0,0) is white (#ffffff)
                pdf_utils.draw_shapely_poly(c, final_bg, CMYKColor(0,0,0,0), alpha=0.03)

                # Draw Text (Black #221f1f - RGB(34,31,31) = CMYK(0,0.09,0.09,0.87))
                pdf_utils.draw_shapely_poly(c, final_text, CMYKColor(0, 0.09, 0.09, 0.87), alpha=1.0)

        # Save PDF
        c.save()
        print(f"Saved: {output_path}")

if __name__ == "__main__":    
    if not os.path.exists(config.FONT_PATH):
        print(f"ERROR: Font not found at {config.FONT_PATH}")
        print("Please place a .ttf file in the assets folder.")
    else:
        process_orders()