import os

# Paths
# Go up from src/ -> app/ -> root/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_DIR = os.path.join(BASE_DIR, 'input_csv')
ORDERS_DIR = os.path.join(INPUT_DIR, 'orders')
CUSTOM_DIR = os.path.join(INPUT_DIR, 'custom')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output_sheet')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
FONT_PATH = os.path.join(ASSETS_DIR, 'fonts', 'Industry_Ultra.ttf')
FLAGS_DIR = os.path.join(ASSETS_DIR, 'flags')

# Page Specs (A4 in points)
MM_TO_PTS = 2.83465
PAGE_WIDTH = 210 * MM_TO_PTS
PAGE_HEIGHT = 297 * MM_TO_PTS
MARGIN = 10 * MM_TO_PTS
GAP = 25 * MM_TO_PTS  # Grid line every 25mm
GRID_SIZE = 25 * MM_TO_PTS  # One grid square = 25mm

# Product Specs
# Sizes based on asset_specs.md (heights in mm)
# All have 0.35mm offset outline for peeling bubble (0.7mm total)
SIZE_MAP = {
    'Words': {'font_size': 5.714 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 4},    # 5.7mm font renders 4mm text height
    'ContainsQ': {'font_size': 7.71425 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 5}, # If text contains 'Q': 5mm
    'ContainsAccents': {'font_size': 7.71425 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 5}, # If text contains accents: 5mm
    'ContainsSlashes': {'font_size': 6.8568 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 4.8}, # If text contains slashes: 4.8mm
    'ContainsCommas': {'font_size': 6.8568 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 4.8}, # If text contains commas: 4.8mm
    'Initials': {'font_size': 6.428 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 4.5},    # Initials + Numbers: 4.5mm
    'Flags': {'font_size': 6 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 6},       # Flags: 6mm
    'Symbols': {'font_size': 10 * MM_TO_PTS, 'offset_mm': 0.35, 'target_height_mm': 10}    # Symbols: 10mm
}
