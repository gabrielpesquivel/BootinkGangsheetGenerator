from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor, magenta
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

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