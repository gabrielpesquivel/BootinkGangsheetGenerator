# Gang Sheet Generator

Automated gang sheet generation tool for Shopify store owners selling custom stickers, decals, and printed products.

## Quick Start (Desktop App)

1. **Run** `dist\GangSheetGenerator.exe`
2. **Drag & drop** your Shopify CSV files into the window
3. **Done!** PDFs appear in `output_sheet/` folder next to the exe

## Features

- **Drag & Drop GUI**: Modern dark-themed interface - just drag CSV files in
- **178 Country Flags**: Full flag support across all regions
- **Smart Layout**: Bin-packing algorithm maximizes sheet usage
- **Multi-Page Support**: Automatically creates new pages when sheets fill up
- **Print-Ready Output**: A4 PDF sheets ready for DTF, sublimation, or vinyl printing
- **Fully Portable**: Single .exe file contains everything

## Installation

### Option 1: Use Pre-built Executable (Recommended)

1. Download `GangSheetGenerator.exe` from the `dist/` folder
2. Double-click to run
3. If Windows SmartScreen appears, click "More info" → "Run anyway"

### Option 2: Run from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI
python app/gui.py

# Or run command-line version (place CSVs in input_csv/ first)
python app/main.py
```

### Option 3: Build Executable Yourself

```bash
pip install -r requirements.txt
cd app
python -m PyInstaller build_exe.spec --noconfirm --distpath ../dist
```

The executable will be created at `dist/GangSheetGenerator.exe`

## Commands

| Command | Description |
|---------|-------------|
| `python app/gui.py` | Launch the GUI application |
| `python app/main.py` | Run command-line version (reads from `input_csv/`) |
| `cd app && python -m PyInstaller build_exe.spec --noconfirm --distpath ../dist` | Build the executable |
| `powershell -ExecutionPolicy Bypass -File app/create_shortcut.ps1` | Create desktop shortcut |

## Create Desktop Shortcut

```powershell
# PowerShell
powershell -ExecutionPolicy Bypass -File app/create_shortcut.ps1

# Or double-click
app/create_shortcut.bat
```

Or manually: Right-click `GangSheetGenerator.exe` → Send to → Desktop

## Usage

### GUI Application
1. Launch `GangSheetGenerator.exe` or run `python gui.py`
2. Drag & drop CSV files into the window (or click to browse)
3. Wait for "Ready!" message
4. Click "Open Output Folder" to view PDFs

### Command Line
```bash
# Place CSVs in input_csv/ folder
python main.py
# PDFs appear in output_sheet/ folder
```

## Shopify CSV Format

Export orders from Shopify Admin → Orders → Export

The tool reads these columns:
- `Lineitem name`: Product name (format: `Region - COUNTRY` or `Category - TEXT / COLOR`)
- `Lineitem quantity`: Number of items

Examples:
| Lineitem name | Output |
|---------------|--------|
| `Europe - WALES` | Wales flag |
| `Asia - JAPAN / BLACK` | Japan flag |
| `Family - SMITH` | Text "SMITH" |
| `Numbers - 23 / BLACK` | Text "23" |

Items containing "Priming Wipe" are automatically excluded.

## Supported Flags (178 total)

| Region | Countries |
|--------|-----------|
| **Europe** (48) | Albania, Austria, Belgium, Bosnia, Croatia, Denmark, England, France, Germany, Greece, Hungary, Italy, Netherlands, Norway, Poland, Portugal, Scotland, Serbia, Slovenia, Spain, Sweden, Switzerland, Ukraine, Wales, + more |
| **Asia** (28) | Bangladesh, Cambodia, China, India, Indonesia, Japan, Malaysia, Pakistan, Philippines, Singapore, South Korea, Thailand, Vietnam, + more |
| **Africa** (36) | Egypt, Ethiopia, Ghana, Kenya, Morocco, Nigeria, South Africa, + more |
| **Americas** (41) | Argentina, Brazil, Canada, Chile, Colombia, Cuba, Jamaica, Mexico, Peru, USA, + more |
| **Oceania** (9) | Australia, Fiji, New Zealand, Papua New Guinea, Samoa, + more |
| **Middle East** (16) | Iran, Iraq, Israel, Jordan, Kuwait, Lebanon, Qatar, Saudi Arabia, UAE, + more |

## Project Structure

```
ShopifyOrdersPipeline/
├── app/                     # Application source code
│   ├── src/
│   │   ├── config.py       # Page size, margins, sizing
│   │   ├── geometry.py     # Text-to-shape conversion
│   │   ├── layout.py       # Smart layout manager
│   │   └── pdf_utils.py    # PDF generation
│   ├── gui.py              # GUI application
│   ├── main.py             # Core processing / CLI
│   ├── build_exe.spec      # PyInstaller config
│   ├── create_shortcut.ps1 # Desktop shortcut script
│   └── create_shortcut.bat # Shortcut script launcher
├── assets/
│   ├── fonts/              # Font files
│   │   └── Industry_Ultra.ttf
│   └── flags/              # Flag SVGs by region
│       ├── africa/
│       ├── asia/
│       ├── caribbean/
│       ├── central_america/
│       ├── europe/
│       ├── middle_east/
│       ├── north_america/
│       ├── oceania/
│       └── south_america/
├── dist/                    # Built executable
│   └── GangSheetGenerator.exe
├── input_csv/              # Place CSV files here (CLI mode)
├── output_sheet/           # Generated PDFs appear here
├── .gitignore
├── README.md
└── requirements.txt
```

## Configuration

Edit `app/src/config.py` to customize:

```python
# Page Settings (A4)
PAGE_WIDTH = 210 * MM_TO_PTS
PAGE_HEIGHT = 297 * MM_TO_PTS
MARGIN = 10 * MM_TO_PTS
GRID_SIZE = 25 * MM_TO_PTS

# Asset Sizes (heights in mm)
SIZE_MAP = {
    'Words': {'target_height_mm': 4},      # Dates + Words over 3 chars
    'Initials': {'target_height_mm': 5},   # Initials + Numbers
    'Flags': {'target_height_mm': 6},      # Country flags
    'Symbols': {'target_height_mm': 10}    # Symbols
}
```

## Requirements

- Python 3.8+
- pandas
- reportlab
- shapely
- matplotlib
- numpy
- svglib
- customtkinter (for GUI)
- tkinterdnd2 (for drag-drop)

## Troubleshooting

### Windows SmartScreen blocks the app
Click "More info" → "Run anyway" (only needed once)

### "Flag file not found" warning
The country name in the CSV doesn't match any flag file. Check spelling matches the files in `assets/flags/`.

### GUI won't start
Try running from source: `python gui.py`

### No output generated
- Check CSV files are valid Shopify exports
- Look for error messages in the status area
- Ensure the CSV has `Lineitem name` and `Lineitem quantity` columns
