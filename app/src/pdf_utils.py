import base64
import io
import shutil
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor, magenta
from reportlab.lib.utils import ImageReader
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

# Pixels per SVG unit when rasterising gradient SVGs
_RASTER_SCALE = 8

# Locate rsvg-convert once at import time
_RSVG_CONVERT = shutil.which('rsvg-convert')


def _rasterize_svg(svg_path):
    """Rasterize an SVG to a PIL Image using rsvg-convert, preserving transparency."""
    if not _RSVG_CONVERT:
        return None
    result = subprocess.run(
        [_RSVG_CONVERT, '-z', str(_RASTER_SCALE), '--format=png', svg_path],
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return Image.open(io.BytesIO(result.stdout))


def _get_svg_viewbox(svg_path):
    """Get the viewBox (or width/height) dimensions of an SVG."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    viewbox = root.get('viewBox', '')
    if viewbox:
        parts = viewbox.split()
        return float(parts[2]), float(parts[3])
    w = root.get('width', '0')
    h = root.get('height', '0')
    w = float(''.join(c for c in w if c.isdigit() or c == '.') or '0')
    h = float(''.join(c for c in h if c.isdigit() or c == '.') or '0')
    return w, h


def _is_raster_svg(svg_path):
    """Check if an SVG needs raster rendering (embedded images or gradients)."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'image':
            return True
        if tag in ('linearGradient', 'radialGradient'):
            return True
    return False


def _extract_raster_from_svg(svg_path):
    """
    Extract or rasterize an SVG to a PIL Image with viewBox dimensions.

    For SVGs with embedded <image> tags, extracts the base64 image directly.
    For SVGs with gradients, rasterizes via cairosvg to preserve gradient rendering.

    Returns:
        (PIL.Image, viewbox_width, viewbox_height) or (None, 0, 0) on failure
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Get viewBox dimensions
    vb_width, vb_height = _get_svg_viewbox(svg_path)

    # First try: extract embedded <image> (base64 PNGs)
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'image':
            href = None
            for attr_name, attr_value in elem.attrib.items():
                if attr_name.endswith('href') and 'base64,' in attr_value:
                    href = attr_value
                    break
            if href:
                b64_data = href.split('base64,', 1)[1]
                img_data = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(img_data))
                return img, vb_width, vb_height

    # Fallback: rasterize the full SVG via cairosvg (handles gradients)
    img = _rasterize_svg(svg_path)
    if img:
        return img, vb_width, vb_height

    return None, 0, 0


def _draw_raster_image(c, img, x, y, target_width, target_height):
    """Draw a PIL Image onto the ReportLab canvas with transparency."""
    img_reader = ImageReader(img)
    c.drawImage(img_reader, x, y, width=target_width, height=target_height, mask='auto')


def get_raster_svg_dimensions(svg_path, target_height_pts):
    """Get dimensions of a raster SVG when scaled to a target height."""
    _, vb_width, vb_height = _extract_raster_from_svg(svg_path)
    if vb_height == 0:
        return 0, 0
    scale = target_height_pts / vb_height
    return vb_width * scale, vb_height * scale


def get_raster_svg_dimensions_by_width(svg_path, target_width_pts):
    """Get dimensions of a raster SVG when scaled to a target width."""
    _, vb_width, vb_height = _extract_raster_from_svg(svg_path)
    if vb_width == 0:
        return 0, 0
    scale = target_width_pts / vb_width
    return vb_width * scale, vb_height * scale


def draw_raster_svg(c, svg_path, x, y, target_height_pts):
    """Draw a raster SVG scaled to target height, preserving transparency."""
    img, vb_width, vb_height = _extract_raster_from_svg(svg_path)
    if img is None:
        return 0, 0
    scale = target_height_pts / vb_height
    w = vb_width * scale
    h = vb_height * scale
    _draw_raster_image(c, img, x, y, w, h)
    return w, h


def draw_raster_svg_by_width(c, svg_path, x, y, target_width_pts):
    """Draw a raster SVG scaled to target width, preserving transparency."""
    img, vb_width, vb_height = _extract_raster_from_svg(svg_path)
    if img is None:
        return 0, 0
    scale = target_width_pts / vb_width
    w = vb_width * scale
    h = vb_height * scale
    _draw_raster_image(c, img, x, y, w, h)
    return w, h

def get_svg_dimensions(svg_path, target_height_pts):
    """
    Get the dimensions of an SVG when scaled to a target height.

    Args:
        svg_path: Path to the SVG file
        target_height_pts: Target height in points

    Returns:
        (width, height) of the scaled SVG in points
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        return 0, 0

    original_height = drawing.height
    original_width = drawing.width
    scale = target_height_pts / original_height

    return original_width * scale, original_height * scale


def get_svg_dimensions_by_width(svg_path, target_width_pts):
    """
    Get the dimensions of an SVG when scaled to a target width.

    Args:
        svg_path: Path to the SVG file
        target_width_pts: Target width in points

    Returns:
        (width, height) of the scaled SVG in points
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        return 0, 0

    original_height = drawing.height
    original_width = drawing.width
    scale = target_width_pts / original_width

    return original_width * scale, original_height * scale

def setup_canvas(output_path, page_size):
    c = canvas.Canvas(output_path, pagesize=page_size)
    return c

def draw_cutting_rectangle(c, x, y, width, height):
    """
    Draw a thin magenta rectangle for cutting machine.

    Args:
        c: ReportLab canvas
        x: Bottom-left x coordinate in points
        y: Bottom-left y coordinate in points
        width: Rectangle width in points
        height: Rectangle height in points
    """
    c.saveState()
    c.setStrokeColor(magenta)  # Magenta color for cutting machine
    c.setLineWidth(0.5)  # Thin line (0.5 points)
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.restoreState()

def draw_svg(c, svg_path, x, y, target_height_pts):
    """
    Draws an SVG file onto the ReportLab canvas at specified position.

    Args:
        c: ReportLab canvas
        svg_path: Path to the SVG file
        x: X position (bottom-left) in points
        y: Y position (bottom-left) in points
        target_height_pts: Target height in points (will scale proportionally)

    Returns:
        (width, height) of the rendered SVG in points
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        return 0, 0

    # Calculate scale factor to achieve target height
    original_height = drawing.height
    original_width = drawing.width
    scale = target_height_pts / original_height

    # Scale the drawing
    drawing.width = original_width * scale
    drawing.height = original_height * scale
    drawing.scale(scale, scale)

    # Render onto canvas
    renderPDF.draw(drawing, c, x, y)

    return drawing.width, drawing.height


def draw_svg_by_width(c, svg_path, x, y, target_width_pts):
    """
    Draws an SVG file onto the ReportLab canvas, scaled to a target width.

    Args:
        c: ReportLab canvas
        svg_path: Path to the SVG file
        x: X position (bottom-left) in points
        y: Y position (bottom-left) in points
        target_width_pts: Target width in points (will scale proportionally)

    Returns:
        (width, height) of the rendered SVG in points
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        return 0, 0

    # Calculate scale factor to achieve target width
    original_height = drawing.height
    original_width = drawing.width
    scale = target_width_pts / original_width

    # Scale the drawing
    drawing.width = original_width * scale
    drawing.height = original_height * scale
    drawing.scale(scale, scale)

    # Render onto canvas
    renderPDF.draw(drawing, c, x, y)

    return drawing.width, drawing.height


def draw_shapely_poly(c, poly, color, alpha=1.0, stroke_color=None, stroke_width=0):
    """Draws a Shapely polygon onto the ReportLab canvas.

    Args:
        c: ReportLab canvas
        poly: Shapely polygon or multipolygon
        color: Fill color (CMYKColor or other)
        alpha: Fill opacity (0.0 to 1.0)
        stroke_color: Optional stroke color
        stroke_width: Stroke width in points
    """
    path = c.beginPath()

    # Handle both Polygon and MultiPolygon
    if poly.geom_type == 'Polygon':
        geoms = [poly]
    else:
        geoms = poly.geoms

    for p in geoms:
        x, y = p.exterior.xy
        path.moveTo(x[0], y[0])
        for i in range(1, len(x)):
            path.lineTo(x[i], y[i])
        path.close()

        # Handle holes (like inside 'O')
        for interior in p.interiors:
            xi, yi = interior.xy
            path.moveTo(xi[0], yi[0])
            for i in range(1, len(xi)):
                path.lineTo(xi[i], yi[i])
            path.close()

    c.saveState()

    # Create color with alpha baked in
    if hasattr(color, 'cyan'):
        # CMYK color - recreate with alpha
        fill_color = CMYKColor(color.cyan, color.magenta, color.yellow, color.black, alpha=alpha)
    else:
        # RGB or other color
        c.setFillAlpha(alpha)
        fill_color = color

    c.setFillColor(fill_color)

    # Handle stroke if specified
    if stroke_color and stroke_width > 0:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
        c.drawPath(path, fill=1, stroke=1)
    else:
        c.drawPath(path, fill=1, stroke=0)
    c.restoreState()