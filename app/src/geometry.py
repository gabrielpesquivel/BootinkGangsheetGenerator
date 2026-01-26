import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity
from . import config


def add_space_bridges(text, text_shape, font_path, font_size):
    """
    Add bridging rectangles at space positions to connect words.
    This ensures stickers come off in one piece.

    Bridge dimensions: 1mm height x 3.6mm width
    The bridge itself is invisible (0% opacity) but contributes to
    the bubble shape, creating a semi-transparent 3% bridge effect.

    Returns:
        (text_shape, shape_for_bubble): text_shape is unchanged for rendering,
        shape_for_bubble includes bridges for creating the bubble outline.
    """
    if ' ' not in text:
        return text_shape, text_shape

    # Bridge dimensions in points
    bridge_height = 1.0 * config.MM_TO_PTS
    bridge_width = 3.6 * config.MM_TO_PTS

    fp = FontProperties(fname=font_path)
    minx, miny, maxx, maxy = text_shape.bounds
    text_center_y = (miny + maxy) / 2

    bridges = []

    # Find space positions by rendering prefix text
    for i, char in enumerate(text):
        if char == ' ':
            # Render text up to this space
            prefix = text[:i]
            if not prefix:
                continue
            tp = TextPath((0, 0), prefix, size=font_size, prop=fp)
            verts = tp.vertices
            if len(verts) == 0:
                continue

            # Right edge of the prefix is where the space starts
            space_x = verts[:, 0].max()

            # Create bridge rectangle
            # x: starts at space_x
            # y: centered on text
            bridge_left = space_x
            bridge_bottom = text_center_y - bridge_height / 2
            bridge_right = bridge_left + bridge_width
            bridge_top = bridge_bottom + bridge_height

            bridge = box(bridge_left, bridge_bottom, bridge_right, bridge_top)
            bridges.append(bridge)

    if bridges:
        shape_for_bubble = unary_union([text_shape] + bridges)
        return text_shape, shape_for_bubble
    return text_shape, text_shape

def text_to_shapely(text, font_path, font_size):
    """Converts a text string into a single united Shapely polygon with proper holes."""
    fp = FontProperties(fname=font_path)
    tp = TextPath((0, 0), text, size=font_size, prop=fp)

    # Flatten the path to convert curves to line segments
    flattened = tp.to_polygons()

    if not flattened:
        # If no polygons, return a small point (fallback)
        return Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

    # Convert to shapely polygons
    raw_polys = []
    for poly_verts in flattened:
        if len(poly_verts) >= 3:  # Need at least 3 points for a polygon
            try:
                poly = Polygon(poly_verts)
                if poly.is_valid and not poly.is_empty:
                    raw_polys.append(poly)
                elif not poly.is_valid:
                    # Try to fix invalid polygons
                    poly = poly.buffer(0)
                    if poly.is_valid and not poly.is_empty:
                        raw_polys.append(poly)
            except Exception:
                continue

    if not raw_polys:
        return Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

    # Sort polygons by area (largest first)
    # This helps identify outer shells vs holes
    raw_polys.sort(key=lambda p: p.area, reverse=True)

    # Build proper polygons with holes
    # Strategy: For each polygon, check if it contains smaller polygons (potential holes)
    result_polys = []
    used = [False] * len(raw_polys)

    for i, outer in enumerate(raw_polys):
        if used[i]:
            continue

        # Find holes for this outer polygon
        holes = []
        for j, inner in enumerate(raw_polys):
            if i != j and not used[j]:
                # Check if inner is contained within outer
                if outer.contains(inner) or outer.covers(inner):
                    # This is a hole
                    holes.append(inner.exterior.coords[:-1])  # Remove duplicate last point
                    used[j] = True

        # Create polygon with holes
        try:
            if holes:
                poly_with_holes = Polygon(outer.exterior.coords, holes=holes)
            else:
                poly_with_holes = outer

            if poly_with_holes.is_valid:
                result_polys.append(poly_with_holes)
            else:
                # Try to fix with buffer
                poly_with_holes = poly_with_holes.buffer(0)
                if poly_with_holes.is_valid and not poly_with_holes.is_empty:
                    result_polys.append(poly_with_holes)
        except Exception:
            # If polygon with holes fails, just add the outer shape
            result_polys.append(outer)

        used[i] = True

    # Union all the polygons (now with proper holes)
    if len(result_polys) == 1:
        return result_polys[0]

    try:
        return unary_union(result_polys)
    except Exception:
        # Last resort: buffer each and union
        buffered = [p.buffer(0) for p in result_polys if p.is_valid]
        return unary_union(buffered) if buffered else result_polys[0]

def create_sticker_geometry(text, font_path, size_config, rect_width, rect_height):
    """
    Returns (text_shape, background_shape, rectangle_width, rectangle_height).
    Text and background are centered within the specified rectangle dimensions.

    Args:
        text: Text string to render
        font_path: Path to font file
        size_config: Size configuration dict with font_size and offset_mm
        rect_width: Target rectangle width in points
        rect_height: Target rectangle height in points
    """

    font_size_pts = size_config['font_size']
    offset_pts = size_config['offset_mm'] * config.MM_TO_PTS

    # 1. Get Base Text
    text_shape = text_to_shapely(text, font_path, font_size_pts)

    # 2. Add bridging rectangles at spaces (for single-piece stickers)
    # text_shape remains unchanged for rendering (bridges are invisible)
    # shape_for_bubble includes bridges to create the bubble outline
    text_shape, shape_for_bubble = add_space_bridges(text, text_shape, font_path, font_size_pts)

    # 3. Create Offset (Background) from shape that includes bridges
    # join_style=1 (Round), resolution=16 (Smoothness)
    # The bubble will span across word gaps via the invisible bridges
    bg_shape = shape_for_bubble.buffer(offset_pts, join_style=1, resolution=16)

    # 4. Get bounds of the background
    minx, miny, maxx, maxy = bg_shape.bounds
    bg_width = maxx - minx
    bg_height = maxy - miny

    # 5. Center the text and background within the rectangle
    # Calculate offset to center both horizontally and vertically
    center_x = (rect_width - bg_width) / 2 - minx
    center_y = (rect_height - bg_height) / 2 - miny

    text_shape = affinity.translate(text_shape, xoff=center_x, yoff=center_y)
    bg_shape = affinity.translate(bg_shape, xoff=center_x, yoff=center_y)

    return text_shape, bg_shape, rect_width, rect_height


def create_two_row_sticker_geometry(text, font_path, size_config, rect_width, rect_height):
    """
    Creates sticker geometry with text split into two rows to fit in a single square.
    Used for custom flag items. Scales down if needed to fit.

    Args:
        text: Text string to render (e.g., "POLAND FLAG")
        font_path: Path to font file
        size_config: Size configuration dict with font_size and offset_mm
        rect_width: Target rectangle width in points
        rect_height: Target rectangle height in points
    """
    offset_pts = size_config['offset_mm'] * config.MM_TO_PTS

    # Split text into two rows - split at space before "FLAG" or at midpoint
    words = text.split()
    if len(words) >= 2:
        # Put all but last word on row 1, last word on row 2
        row1 = ' '.join(words[:-1])
        row2 = words[-1]
    else:
        # Single word - split at midpoint
        mid = len(text) // 2
        row1 = text[:mid]
        row2 = text[mid:]

    # Start with the configured font size and scale down if needed
    base_font_size = size_config['font_size']
    max_iterations = 10
    scale_factor = 1.0

    for iteration in range(max_iterations):
        font_size_pts = base_font_size * scale_factor
        line_spacing = font_size_pts * 0.3  # Space between rows

        # Create shapes for each row
        row1_shape = text_to_shapely(row1, font_path, font_size_pts)
        row2_shape = text_to_shapely(row2, font_path, font_size_pts)

        # Add bridging rectangles at spaces for each row
        # For two-row stickers, we use the combined shape (with bridges) for both
        # rendering and bubble since this is a placeholder implementation
        _, row1_shape = add_space_bridges(row1, row1_shape, font_path, font_size_pts)
        _, row2_shape = add_space_bridges(row2, row2_shape, font_path, font_size_pts)

        # Get bounds of each row
        r1_minx, r1_miny, r1_maxx, r1_maxy = row1_shape.bounds
        r2_minx, r2_miny, r2_maxx, r2_maxy = row2_shape.bounds

        r1_width = r1_maxx - r1_minx
        r1_height = r1_maxy - r1_miny
        r2_width = r2_maxx - r2_minx
        r2_height = r2_maxy - r2_miny

        # Position row2 below row1
        # Move row1 to origin first
        row1_shape = affinity.translate(row1_shape, xoff=-r1_minx, yoff=-r1_miny)
        # Move row2 below row1
        row2_shape = affinity.translate(row2_shape, xoff=-r2_minx, yoff=-r2_miny - r1_height - line_spacing)

        # Combine into single shape
        combined_shape = unary_union([row1_shape, row2_shape])

        # Create background
        bg_shape = combined_shape.buffer(offset_pts, join_style=1, resolution=16)

        # Get combined bounds
        minx, miny, maxx, maxy = bg_shape.bounds
        total_width = maxx - minx
        total_height = maxy - miny

        # Check if it fits within the rectangle (with some margin)
        margin = rect_width * 0.05  # 5% margin
        available_width = rect_width - margin * 2
        available_height = rect_height - margin * 2

        if total_width <= available_width and total_height <= available_height:
            # It fits! Center and return
            center_x = (rect_width - total_width) / 2 - minx
            center_y = (rect_height - total_height) / 2 - miny

            combined_shape = affinity.translate(combined_shape, xoff=center_x, yoff=center_y)
            bg_shape = affinity.translate(bg_shape, xoff=center_x, yoff=center_y)

            return combined_shape, bg_shape, rect_width, rect_height

        # Scale down for next iteration
        scale_factor *= 0.85

    # Final fallback - use the last scaled version and force center it
    center_x = (rect_width - total_width) / 2 - minx
    center_y = (rect_height - total_height) / 2 - miny

    combined_shape = affinity.translate(combined_shape, xoff=center_x, yoff=center_y)
    bg_shape = affinity.translate(bg_shape, xoff=center_x, yoff=center_y)

    return combined_shape, bg_shape, rect_width, rect_height