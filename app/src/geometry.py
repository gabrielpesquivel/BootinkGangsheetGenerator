import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity
from . import config

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

    # 2. Create Offset (Background)
    # join_style=1 (Round), resolution=16 (Smoothness)
    bg_shape = text_shape.buffer(offset_pts, join_style=1, resolution=16)

    # 3. Get bounds of the background
    minx, miny, maxx, maxy = bg_shape.bounds
    bg_width = maxx - minx
    bg_height = maxy - miny

    # 4. Center the text and background within the rectangle
    # Calculate offset to center both horizontally and vertically
    center_x = (rect_width - bg_width) / 2 - minx
    center_y = (rect_height - bg_height) / 2 - miny

    text_shape = affinity.translate(text_shape, xoff=center_x, yoff=center_y)
    bg_shape = affinity.translate(bg_shape, xoff=center_x, yoff=center_y)

    return text_shape, bg_shape, rect_width, rect_height