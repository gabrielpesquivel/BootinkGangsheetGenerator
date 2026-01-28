# Gang Sheet Generator

Automated gang sheet generation tool for Shopify store owners selling custom stickers, decals, and printed products. Converts Shopify order exports into print-ready PDF gang sheets with optimized layouts.

## Quick Start

1. Run `dist/GangSheetGenerator.exe`
2. Drag & drop your Shopify CSV files into the window
3. PDFs appear in `output_sheet/` folder

## Features

### Content Support
- **184 Country Flags** - Full coverage across 9 regions worldwide
- **30+ Symbols** - Animals, popular icons, and religious symbols in black/white variants
- **Custom Text** - Names, initials, numbers, dates, and custom verses
- **Custom Flags** - Request-a-flag with two-row layout (country name + "FLAG")

### Technical Features
- **Smart Layout** - Bin-packing algorithm maximizes sheet usage
- **Multi-Page Support** - Automatically creates new pages when sheets fill up
- **Invisible Bridges** - Connects multi-word stickers so they peel off as one piece
- **Bubble Outlines** - Semi-transparent 3% outline for easy peeling
- **Dual PDF Output** - With and without cutting borders
- **Error Handling** - Invalid items shown in fluorescent yellow with order numbers

### Application
- **Drag & Drop GUI** - Modern dark-themed interface
- **Command Line** - Batch processing support
- **Fully Portable** - Single .exe contains everything

## Installation

### Option 1: Pre-built Executable (Recommended)

1. Download `GangSheetGenerator.exe` from `dist/` folder
2. Double-click to run
3. If Windows SmartScreen appears, click "More info" → "Run anyway"

### Option 2: Run from Source

```bash
pip install -r requirements.txt
python app/gui.py
```

### Option 3: Build Executable

```bash
pip install -r requirements.txt
cd app
python -m PyInstaller build_exe.spec --noconfirm --distpath ../dist
```

## Usage

### GUI Application

1. Launch `GangSheetGenerator.exe` or `python app/gui.py`
2. Drag & drop CSV files (or click to browse)
3. Wait for processing to complete
4. Click "Open Output Folder" to view PDFs

### Command Line

```bash
# Place order CSVs in input_csv/orders/
# Place custom value CSVs in input_csv/custom/
python app/main.py
# PDFs appear in output_sheet/
```

## CSV Format

### Orders CSV

Export from Shopify Admin → Orders → Export. Required columns:

| Column | Description |
|--------|-------------|
| `Name` | Order number (e.g., #1234) |
| `Lineitem name` | Product name with format info |
| `Lineitem quantity` | Number of items |

### Lineitem Name Formats

| Format | Example | Output |
|--------|---------|--------|
| Flag | `Europe - WALES` | Wales flag |
| Flag with color | `Asia - JAPAN / BLACK` | Japan flag |
| Symbol | `Animals - LION / BLACK` | Black lion symbol |
| Symbol | `Religious Icons - HALO / WHITE` | White halo symbol |
| Text | `Family - SMITH / BLACK` | "SMITH" text sticker |
| Numbers | `Numbers - 23 / WHITE` | "23" text sticker |

### Custom Items CSV

For personalized items, place a separate CSV in `input_csv/custom/` with:

| Column | Description |
|--------|-------------|
| `Name` | Order number (must match orders CSV) |
| `Lineitem name` | Product name (must match orders CSV) |
| `Lineitem Attribute Key` | Custom field name |
| `Lineitem Attribute Value` | Customer's custom value |

**Supported Custom Patterns:**
- `CUSTOM TEXT`, `CUSTOM NAME`, `FIRST NAME`, `LAST NAME`
- `CUSTOM INITIALS`, `CUSTOM NUMBERS`, `CUSTOM NUMBER`
- `CUSTOM VERSE`, `PERIODS`, `SLASHES`
- `REQUEST A FLAG` (creates two-row layout with "FLAG" suffix)

## Supported Assets

### Flags (184 total)

| Region | Count | Examples |
|--------|-------|----------|
| Europe | 48 | England, France, Germany, Italy, Poland, Spain, Wales |
| Asia | 28 | China, India, Japan, Philippines, South Korea, Thailand |
| Africa | 36 | Egypt, Ghana, Kenya, Morocco, Nigeria, South Africa |
| North America | 3 | Canada, Mexico, USA |
| South America | 12 | Argentina, Brazil, Chile, Colombia, Peru |
| Central America | 7 | Costa Rica, Guatemala, Honduras, Panama |
| Caribbean | 25 | Cuba, Dominican Republic, Jamaica, Puerto Rico |
| Middle East | 16 | Iran, Iraq, Israel, Lebanon, Saudi Arabia, UAE |
| Oceania | 9 | Australia, Fiji, New Zealand, Samoa |

### Symbols

| Category | Symbols |
|----------|---------|
| **Animals** | Bull, Butterfly, Cobra, Dove, Goat, Lion, Tiger |
| **Popular** | Alien, Crown, Dollar Sign, Gladiator, Lightning Bolt, Love Heart, Skull, Twin |
| **Religious** | Angel Wings, Christian Cross, Dove, Halo, Orthodox Cross, Star and Crescent, Star of David, The Ankh, Wheel of the Law, Ying and Yang |

All symbols available in Black and White variants (some colorless).

## Sizing Specifications

| Item Type | Target Height | Grid Squares |
|-----------|---------------|--------------|
| Words (3+ chars) | 4mm | 1-3 (based on length) |
| Initials (1-2 chars) | 4.5mm | 1 |
| Flags | 6mm | 1 |
| Symbols | 10mm | 1 |
| Crowns & Hearts | 8mm | 1 |
| Halos | 10mm width | 1 |

**Grid:** 25mm squares on A4 sheets (210×297mm) with 10mm margins.

## Project Structure

```
ShopifyOrdersPipeline/
├── app/
│   ├── src/
│   │   ├── config.py        # Page size, margins, sizing
│   │   ├── geometry.py      # Text-to-shape, bridges
│   │   ├── layout.py        # Bin-packing layout manager
│   │   └── pdf_utils.py     # PDF generation, SVG rendering
│   ├── gui.py               # GUI application
│   ├── main.py              # Core processing / CLI
│   ├── build_exe.spec       # PyInstaller config
│   └── create_shortcut.*    # Desktop shortcut scripts
├── assets/
│   ├── fonts/
│   │   └── Industry_Ultra.ttf
│   ├── flags/               # SVGs organized by region
│   │   ├── africa/
│   │   ├── asia/
│   │   ├── caribbean/
│   │   ├── central_america/
│   │   ├── europe/
│   │   ├── middle_east/
│   │   ├── north_america/
│   │   ├── oceania/
│   │   └── south_america/
│   └── symbols/             # SVGs organized by category
│       ├── animals/
│       ├── popular/
│       └── religious/
├── input_csv/
│   ├── orders/              # Shopify order exports
│   └── custom/              # Custom value lookups
├── output_sheet/            # Generated PDFs
├── dist/
│   └── GangSheetGenerator.exe
├── requirements.txt
└── README.md
```

## Configuration

Edit `app/src/config.py`:

```python
# Page Settings (A4)
PAGE_WIDTH = 210 * MM_TO_PTS   # 595 points
PAGE_HEIGHT = 297 * MM_TO_PTS  # 842 points
MARGIN = 10 * MM_TO_PTS        # 28 points
GRID_SIZE = 25 * MM_TO_PTS     # 71 points

# Sizing (heights in mm, with 0.35mm bubble outline)
SIZE_MAP = {
    'Words': {'font_size': 5.714 * MM_TO_PTS, 'target_height_mm': 4},
    'Initials': {'font_size': 6.428 * MM_TO_PTS, 'target_height_mm': 4.5},
    'Flags': {'target_height_mm': 6},
    'Symbols': {'target_height_mm': 10}
}
```

## Technical Details

### Bridge System

Text stickers use an invisible full-width bridge to ensure they peel off as one piece:

- **Purpose:** Connects all characters so the sticker peels as a single unit
- **Height:** 1mm, centered vertically on the text
- **Coverage:** Spans from the leftmost character to the rightmost character
- **Contour-Following:** The bridge follows the actual letter shapes to avoid visual overhang
  - Left edge follows the **right contour** of the leftmost character
  - Right edge follows the **left contour** of the rightmost character
  - Everything in between is filled solid
- **Visibility:** 0% opacity (invisible, but contributes to the 3% bubble outline)

**How it works:**

For text like "HELLO WORLD", the bridge creates a 1mm tall band at the vertical center of the text. Within this band:
1. The left edge aligns with where the "H" actually exists at each Y-level (not its bounding box)
2. The right edge aligns with where the "D" actually exists at each Y-level
3. All gaps between characters (including spaces) are filled

This prevents overhang on letters like "Y" or "T" where the arms/crossbar extend beyond the stem - the bridge only extends to where the letter exists at the bridge's vertical position.

**Applies to:**
- All text items with 2+ characters (Words, Initials)
- Text with spaces (e.g., "HELLO WORLD")
- Text with punctuation (e.g., "A.B")

**Does not apply to:**
- Single characters (no bridge needed)
- SVG assets (flags, symbols)
- Custom flags (two-row placeholder layout)

### Output Files

Each order CSV generates two PDFs:
- `*_gangsheet.pdf` - With magenta cutting borders
- `*_gangsheet_no_border.pdf` - Without borders (for pre-cut workflows)

### Character Width Rules

| Character Count | Grid Squares | Width |
|-----------------|--------------|-------|
| 1-6 | 1 | 25mm |
| 7-14 | 2 | 50mm |
| 15+ | 3 | 75mm |

## Requirements

- Python 3.8+
- pandas
- reportlab
- shapely
- matplotlib
- numpy
- svglib
- customtkinter
- tkinterdnd2

## Troubleshooting

### Windows SmartScreen blocks the app
Click "More info" → "Run anyway" (first run only)

### "Flag file not found" warning
Country name doesn't match flag file. Check spelling in `assets/flags/`.

### "Symbol not found" warning
Symbol name or category doesn't match. Format: `Category - SYMBOL NAME / COLOR`

### Missing custom value
Order number or lineitem name mismatch between orders and custom CSVs.

### GUI won't start
Run from source: `python app/gui.py` to see error messages.

### No output generated
- Verify CSV is valid Shopify export
- Check for `Lineitem name` and `Lineitem quantity` columns
- Look for error messages in status area

### Items excluded
- "Priming Wipe" items are automatically skipped
- Empty or whitespace-only text is skipped

## Commands Reference

| Command | Description |
|---------|-------------|
| `python app/gui.py` | Launch GUI |
| `python app/main.py` | Run CLI (reads from input_csv/) |
| `cd app && python -m PyInstaller build_exe.spec --noconfirm --distpath ../dist` | Build executable |
| `powershell -ExecutionPolicy Bypass -File app/create_shortcut.ps1` | Create desktop shortcut |
