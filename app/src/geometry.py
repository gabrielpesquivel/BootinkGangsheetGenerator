import numpy as np
import re
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, box, LineString, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from shapely import affinity
from . import config


def _get_right_boundary_points(geometry, y_bottom, y_top, num_samples=50):
    """
    Get points along the right boundary of a geometry within a Y range.
    Returns list of (x, y) tuples tracing the rightmost edge at each Y level.
    """
    points = []
    minx, _, maxx, _ = geometry.bounds

    for i in range(num_samples):
        y = y_bottom + (y_top - y_bottom) * i / (num_samples - 1)
        # Create a horizontal line spanning the geometry
        line = LineString([(minx - 1, y), (maxx + 1, y)])
        intersection = geometry.intersection(line)

        if intersection.is_empty:
            continue

        # Find the rightmost x coordinate from the intersection
        max_x = None
        if hasattr(intersection, 'geoms'):
            # MultiLineString - find rightmost point across all segments
            for seg in intersection.geoms:
                if hasattr(seg, 'coords'):
                    for coord in seg.coords:
                        if max_x is None or coord[0] > max_x:
                            max_x = coord[0]
        elif hasattr(intersection, 'coords'):
            # Single LineString or Point
            for coord in intersection.coords:
                if max_x is None or coord[0] > max_x:
                    max_x = coord[0]

        if max_x is not None:
            points.append((max_x, y))

    return points


def _get_left_boundary_points(geometry, y_bottom, y_top, num_samples=50):
    """
    Get points along the left boundary of a geometry within a Y range.
    Returns list of (x, y) tuples tracing the leftmost edge at each Y level.
    """
    points = []
    minx, _, maxx, _ = geometry.bounds

    for i in range(num_samples):
        y = y_bottom + (y_top - y_bottom) * i / (num_samples - 1)
        # Create a horizontal line spanning the geometry
        line = LineString([(minx - 1, y), (maxx + 1, y)])
        intersection = geometry.intersection(line)

        if intersection.is_empty:
            continue

        # Find the leftmost x coordinate from the intersection
        min_x = None
        if hasattr(intersection, 'geoms'):
            # MultiLineString - find leftmost point across all segments
            for seg in intersection.geoms:
                if hasattr(seg, 'coords'):
                    for coord in seg.coords:
                        if min_x is None or coord[0] < min_x:
                            min_x = coord[0]
        elif hasattr(intersection, 'coords'):
            # Single LineString or Point
            for coord in intersection.coords:
                if min_x is None or coord[0] < min_x:
                    min_x = coord[0]

        if min_x is not None:
            points.append((min_x, y))

    return points


def _get_geometry_components(geometry):
    """Extract individual polygon components from any geometry type."""
    components = []
    if isinstance(geometry, MultiPolygon):
        components = list(geometry.geoms)
    elif isinstance(geometry, GeometryCollection):
        for geom in geometry.geoms:
            if isinstance(geom, Polygon) and not geom.is_empty:
                components.append(geom)
            elif isinstance(geom, MultiPolygon):
                components.extend(geom.geoms)
    elif isinstance(geometry, Polygon) and not geometry.is_empty:
        components = [geometry]
    return components


def add_full_width_bridge(text, text_shape, font_path, font_size):
    """
    Create a bridge spanning from the leftmost to rightmost character.
    The bridge follows the contours of the letters to avoid overhang.

    Bridge height: 1mm, centered vertically on text
    Left edge: Follows the right contour of the leftmost character
    Right edge: Follows the left contour of the rightmost character
    Middle: Solid fill between the two edges

    Returns:
        (text_shape, shape_for_bubble): text_shape is unchanged for rendering,
        shape_for_bubble includes the bridge for creating the bubble outline.
    """
    # Strip whitespace for character count check
    stripped_text = text.strip()

    # Skip single character text - no bridge needed
    if len(stripped_text) < 2:
        return text_shape, text_shape

    # Bridge height in points
    bridge_height = 1.0 * config.MM_TO_PTS

    minx, miny, maxx, maxy = text_shape.bounds
    text_center_y = (miny + maxy) / 2

    # Define the vertical range for bridge
    bridge_bottom = text_center_y - bridge_height / 2
    bridge_top = bridge_bottom + bridge_height

    # Create the 1mm band spanning full text width
    band = box(minx - 1, bridge_bottom, maxx + 1, bridge_top)

    # Get text geometry within the band
    text_in_band = text_shape.intersection(band)

    if text_in_band.is_empty:
        return text_shape, text_shape

    # Get all polygon components from the intersection
    components = _get_geometry_components(text_in_band)

    if not components:
        return text_shape, text_shape

    # Sort components by their leftmost x coordinate
    components.sort(key=lambda c: c.bounds[0])

    # Get leftmost and rightmost components
    leftmost_component = components[0]
    rightmost_component = components[-1]

    # If there's only one component (single character in band), no bridge needed
    if len(components) == 1:
        # Check if this single component spans multiple characters by comparing
        # its width to what we'd expect from a single character
        comp_width = leftmost_component.bounds[2] - leftmost_component.bounds[0]
        text_width = maxx - minx
        # If the component is less than 80% of total width, there might be gaps
        # we need to fill, but with only one component, we can't determine edges
        # In this case, the text likely has no gaps in the bridge band
        return text_shape, text_shape

    # Get the right boundary of the leftmost character (where bridge starts)
    right_boundary = _get_right_boundary_points(leftmost_component, bridge_bottom, bridge_top)

    # Get the left boundary of the rightmost character (where bridge ends)
    left_boundary = _get_left_boundary_points(rightmost_component, bridge_bottom, bridge_top)

    if not right_boundary or not left_boundary:
        return text_shape, text_shape

    # Check if the bridge would have negative width (characters overlap or touch)
    # Compare the rightmost point of left char with leftmost point of right char
    right_edge_x = max(pt[0] for pt in right_boundary)
    left_edge_x = min(pt[0] for pt in left_boundary)

    if right_edge_x >= left_edge_x:
        # Characters touch or overlap in the bridge band - no bridge needed
        # But we should still fill any gaps between middle characters
        # Union all components to create the shape_for_bubble
        shape_for_bubble = unary_union([text_shape] + components)
        return text_shape, shape_for_bubble

    # Create bridge polygon: right boundary going up, then left boundary going down
    # This creates a polygon that follows the contours of both edge characters
    bridge_coords = right_boundary + list(reversed(left_boundary))

    # Ensure we have enough points for a valid polygon
    if len(bridge_coords) < 3:
        return text_shape, text_shape

    try:
        bridge = Polygon(bridge_coords)
        if not bridge.is_valid:
            bridge = bridge.buffer(0)  # Fix self-intersections

        if bridge.is_valid and not bridge.is_empty:
            shape_for_bubble = unary_union([text_shape, bridge])
            return text_shape, shape_for_bubble
    except Exception:
        pass

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

    # 2. Add full-width bridge (for single-piece stickers)
    # text_shape remains unchanged for rendering (bridge is invisible)
    # shape_for_bubble includes the bridge to create the bubble outline
    text_shape, shape_for_bubble = add_full_width_bridge(text, text_shape, font_path, font_size_pts)

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
        # Note: Custom flags (two-row stickers) do not use the full-width bridge
        # as they are a placeholder implementation
        row1_shape = text_to_shapely(row1, font_path, font_size_pts)
        row2_shape = text_to_shapely(row2, font_path, font_size_pts)

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