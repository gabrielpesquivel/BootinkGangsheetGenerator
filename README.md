# Gangsheet Generator

Automated gangsheet generation tool for Shopify store owners selling custom stickers, decals, and printed products.

## What It Does

This tool automatically converts Shopify order exports into print-ready PDF gangsheets, eliminating hours of manual layout work. Simply export your orders from Shopify, run the script, and get optimised print sheets ready for production.

## How It Benefits Shopify Store Owners

### Time Savings
- **From Hours to Seconds**: What used to take 2-3 hours of manual design work now takes seconds
- **Batch Processing**: Process multiple order files at once
- **Zero Manual Layout**: No more copying, pasting, and arranging designs in Photoshop or Illustrator

### Error Reduction
- **Automated Parsing**: Directly reads Shopify CSV exports - no manual data entry
- **Accurate Quantities**: Automatically repeats designs based on order quantities
- **Smart Filtering**: Excludes non-printable items (like "Priming Wipe") automatically

### Production Efficiency
- **Optimized Layouts**: Smart packing algorithm maximises sheet usage
- **Multi-Page Support**: Automatically creates new pages when sheets fill up
- **Print-Ready Output**: High-quality PDF output ready for DTF, sublimation, or vinyl printing

### Cost Savings
- **Material Optimization**: Efficient packing reduces wasted material
- **Labor Reduction**: Eliminates manual pre-press work
- **Faster Turnaround**: Ship orders faster with automated production prep

## Features

- **Automatic CSV Processing**: Reads Shopify order exports directly
- **Smart Text Extraction**: Parses product names to extract custom text and designs
- **Configurable Sizes**: Support for Small, Medium, and Large product variations
- **Intelligent Layout**: Bin-packing algorithm optimizes sheet usage
- **Professional Output**: A4 PDF sheets with proper margins and spacing
- **Vector Text Rendering**: Clean, scalable text output with background offsets
- **Batch Processing**: Process multiple order files in one run                                                               

### Usage

1. **Export Orders from Shopify**:
   - Go to Shopify Admin > Orders
   - Select the orders you want to fulfill
   - Export as CSV

2. **Place CSV in Input Folder**:
   - Copy your Shopify CSV export to the `input_csv` folder
   - You can process multiple CSV files at once

3. **Run the Generator**:
```bash
python main.py
```

4. **Get Your Gangsheets**:
   - Find your print-ready PDFs in the `output_sheet` folder
   - Each file will be named `[original_filename]_gangsheet.pdf`

## Example Workflow

```
Shopify Orders (orders.csv)
         ↓
input_csv/orders.csv
         ↓
    python main.py
         ↓
output_sheet/orders_gangsheet.pdf
         ↓
    Send to Printer
```

## Project Structure

```
BootinkProject/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── input_csv/              # Place your Shopify CSV exports here
│   └── example1.csv
├── output_sheet/           # Generated PDF gangsheets appear here
│   └── example1_gangsheet.pdf
├── assets/                 # Font files
│   └── Arial_Bold.ttf
└── src/
    ├── config.py          # Configuration (page size, margins, product sizes)
    ├── pdf_utils.py       # PDF generation utilities
    ├── layout.py          # Smart layout manager
    └── geometry.py        # Text-to-shape conversion
```

## How It Works

### 1. CSV Parsing (main.py:24-50)
The tool reads Shopify order exports and extracts:
- Product names (lineitem name)
- Quantities (lineitem quantity)
- Custom text from product names (format: "Category - TEXT / COLOR")

### 2. Geometry Generation (geometry.py:94-117)
For each unique design:
- Converts text to vector paths using matplotlib
- Creates background offset for sticker borders
- Handles complex characters with holes (like O, P, A, etc.)
- Normalizes sizing for consistent output

### 3. Smart Layout (layout.py:11-42)
The layout manager:
- Uses bin-packing algorithm to fit designs efficiently
- Maintains proper margins (10mm) and gaps (5mm)
- Creates new pages automatically when full
- Tracks cursor position for optimal placement

### 4. PDF Generation (pdf_utils.py)
Outputs production-ready PDFs with:
- A4 page size (210x297mm)
- CMYK color space for print accuracy
- Vector shapes for crisp output at any scale
- Transparency support for layered designs

## Configuration

Edit `src/config.py` to customize:

### Page Settings
```python
PAGE_WIDTH = 210 * MM_TO_PTS   # A4 width
PAGE_HEIGHT = 297 * MM_TO_PTS  # A4 height
MARGIN = 10 * MM_TO_PTS        # 10mm margins
GAP = 5 * MM_TO_PTS            # 5mm gap between stickers
```

### Product Sizes
```python
SIZE_MAP = {
    'Small': {'font_size': 30, 'offset_mm': 1.5},
    'Medium': {'font_size': 50, 'offset_mm': 2.0},
    'Large': {'font_size': 80, 'offset_mm': 3.0}
}
```

### Font
Replace `assets/Arial_Bold.ttf` with any TrueType font you prefer.

## Shopify CSV Format

The tool expects Shopify's standard order export format with these columns:
- `Lineitem name`: Product name (format: "Category - TEXT / COLOR")
- `Lineitem quantity`: Number of items ordered

Example line items:
- `Europe - WALES` → Prints "WALES"
- `Family - CUSTOM TEXT / BLACK` → Prints "CUSTOM TEXT"
- `Numbers - 2 / BLACK` → Prints "2"

Items containing "Priming Wipe" are automatically excluded from printing.

## Requirements

- Python 3.7+
- pandas: CSV processing
- reportlab: PDF generation
- shapely: Geometric operations
- matplotlib: Text-to-path conversion
- numpy: Numerical operations

## Troubleshooting

### "No CSV files found"
- Ensure CSV files are in the `input_csv` folder
- Check that files have `.csv` extension

### "Font not found"
- Verify `Arial_Bold.ttf` exists in the `assets` folder
- Update `FONT_PATH` in config.py if using a different font

### Items Not Appearing
- Check that product names follow the expected format
- Verify the item isn't being filtered (like "Priming Wipe")
- Review console output for skipped items

To-do Notes:
- All countries currently mapped to Australia
- "Custom number" & "Custom text"
- Still more assets to map