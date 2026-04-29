from __future__ import annotations

import math
from dataclasses import dataclass
from functools import partial, reduce, wraps
from itertools import chain, count, islice, starmap
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

Point = tuple[float, float]
Polygon = tuple[Point, ...]
PolygonStream = Iterable[Polygon]

EPSILON = 1e-9


def as_polygon(vertices: Iterable[Point]) -> Polygon:
    return tuple((float(x), float(y)) for x, y in vertices)


def map_polygons(transform: Callable[[Polygon], Polygon], polygons: PolygonStream) -> Iterator[Polygon]:
    return map(transform, polygons)


def filter_polygons(predicate: Callable[[Polygon], bool], polygons: PolygonStream) -> Iterator[Polygon]:
    return filter(predicate, polygons)


def polygon_edges(polygon: Polygon) -> Iterator[tuple[Point, Point]]:
    return zip(polygon, polygon[1:] + polygon[:1])


def point_translate(point: Point, dx: float, dy: float) -> Point:
    x, y = point
    return (x + dx, y + dy)


def point_rotate(point: Point, angle: float, center: Point = (0.0, 0.0)) -> Point:
    x, y = point
    cx, cy = center
    tx, ty = x - cx, y - cy
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return (cx + tx * cos_a - ty * sin_a, cy + tx * sin_a + ty * cos_a)


def point_homothety(point: Point, scale: float, center: Point = (0.0, 0.0)) -> Point:
    x, y = point
    cx, cy = center
    return (cx + scale * (x - cx), cy + scale * (y - cy))


def point_reflect(point: Point, axis: str = "x") -> Point:
    x, y = point
    if axis == "x":
        return (x, -y)
    if axis == "y":
        return (-x, y)
    if axis in {"origin", "xy"}:
        return (-x, -y)
    if axis == "y=x":
        return (y, x)
    if axis == "y=-x":
        return (-y, -x)
    raise ValueError(f"Unsupported symmetry axis: {axis}")


def point_distance(a: Point, b: Point = (0.0, 0.0)) -> float:
    return math.dist(a, b)


def cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def polygon_area(polygon: Polygon) -> float:
    raw = reduce(
        lambda acc, edge: acc + edge[0][0] * edge[1][1] - edge[1][0] * edge[0][1],
        polygon_edges(polygon),
        0.0,
    )
    return abs(raw) / 2.0


def polygon_perimeter(polygon: Polygon) -> float:
    return reduce(lambda acc, edge: acc + math.dist(*edge), polygon_edges(polygon), 0.0)


def polygon_centroid(polygon: Polygon) -> Point:
    area_factor = reduce(
        lambda acc, edge: acc + edge[0][0] * edge[1][1] - edge[1][0] * edge[0][1],
        polygon_edges(polygon),
        0.0,
    )
    if abs(area_factor) < EPSILON:
        xs, ys = zip(*polygon)
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    cx = reduce(
        lambda acc, edge: acc + (edge[0][0] + edge[1][0]) * (edge[0][0] * edge[1][1] - edge[1][0] * edge[0][1]),
        polygon_edges(polygon),
        0.0,
    )
    cy = reduce(
        lambda acc, edge: acc + (edge[0][1] + edge[1][1]) * (edge[0][0] * edge[1][1] - edge[1][0] * edge[0][1]),
        polygon_edges(polygon),
        0.0,
    )
    scale = 1 / (3 * area_factor)
    return (cx * scale, cy * scale)


def side_lengths(polygon: Polygon) -> Iterator[float]:
    return starmap(math.dist, polygon_edges(polygon))


def min_side_length(polygon: Polygon) -> float:
    return min(side_lengths(polygon))


def max_side_length(polygon: Polygon) -> float:
    return max(side_lengths(polygon))


def polygon_angles(polygon: Polygon) -> tuple[float, ...]:
    total = len(polygon)
    angles = []
    for i in range(total):
        prev_p = polygon[i - 1]
        curr_p = polygon[i]
        next_p = polygon[(i + 1) % total]
        v1 = (prev_p[0] - curr_p[0], prev_p[1] - curr_p[1])
        v2 = (next_p[0] - curr_p[0], next_p[1] - curr_p[1])
        denom = math.hypot(*v1) * math.hypot(*v2)
        if denom < EPSILON:
            angles.append(0.0)
            continue
        cos_value = max(-1.0, min(1.0, dot(v1, v2) / denom))
        angles.append(math.acos(cos_value))
    return tuple(angles)


def is_point_on_segment(point: Point, a: Point, b: Point) -> bool:
    if abs(cross(a, b, point)) > EPSILON:
        return False
    return (
        min(a[0], b[0]) - EPSILON <= point[0] <= max(a[0], b[0]) + EPSILON
        and min(a[1], b[1]) - EPSILON <= point[1] <= max(a[1], b[1]) + EPSILON
    )


def point_in_convex_polygon(point: Point, polygon: Polygon) -> bool:
    orientations = tuple(
        cross(a, b, point)
        for a, b in polygon_edges(polygon)
        if not is_point_on_segment(point, a, b)
    )
    if not orientations:
        return True
    non_negative = all(value >= -EPSILON for value in orientations)
    non_positive = all(value <= EPSILON for value in orientations)
    return non_negative or non_positive


def segments_intersect(seg1: tuple[Point, Point], seg2: tuple[Point, Point]) -> bool:
    a, b = seg1
    c, d = seg2
    o1 = cross(a, b, c)
    o2 = cross(a, b, d)
    o3 = cross(c, d, a)
    o4 = cross(c, d, b)

    if (o1 > EPSILON and o2 < -EPSILON or o1 < -EPSILON and o2 > EPSILON) and (
        o3 > EPSILON and o4 < -EPSILON or o3 < -EPSILON and o4 > EPSILON
    ):
        return True

    checks = (
        (abs(o1) <= EPSILON and is_point_on_segment(c, a, b)),
        (abs(o2) <= EPSILON and is_point_on_segment(d, a, b)),
        (abs(o3) <= EPSILON and is_point_on_segment(a, c, d)),
        (abs(o4) <= EPSILON and is_point_on_segment(b, c, d)),
    )
    return any(checks)


def polygons_intersect(first: Polygon, second: Polygon) -> bool:
    if any(segments_intersect(e1, e2) for e1 in polygon_edges(first) for e2 in polygon_edges(second)):
        return True
    return point_in_convex_polygon(first[0], second) or point_in_convex_polygon(second[0], first)


@dataclass(frozen=True)
class PolygonTransform:
    transform: Callable[[Polygon], Polygon]
    name: str

    def __call__(self, target):
        if callable(target):
            @wraps(target)
            def wrapper(*args, **kwargs):
                return map(self.transform, target(*args, **kwargs))

            return wrapper
        return self.transform(target)


@dataclass(frozen=True)
class PolygonPredicate:
    predicate: Callable[[Polygon], bool]
    name: str

    def __call__(self, target):
        if callable(target):
            @wraps(target)
            def wrapper(*args, **kwargs):
                return filter(self.predicate, target(*args, **kwargs))

            return wrapper
        return self.predicate(target)


def tr_translate(dx: float, dy: float) -> PolygonTransform:
    return PolygonTransform(
        transform=lambda polygon: as_polygon(map(lambda point: point_translate(point, dx, dy), polygon)),
        name="tr_translate",
    )


def tr_rotate(angle: float, center: Point = (0.0, 0.0)) -> PolygonTransform:
    return PolygonTransform(
        transform=lambda polygon: as_polygon(map(lambda point: point_rotate(point, angle, center), polygon)),
        name="tr_rotate",
    )


def tr_symmetry(axis: str = "x") -> PolygonTransform:
    return PolygonTransform(
        transform=lambda polygon: as_polygon(map(lambda point: point_reflect(point, axis), polygon)),
        name="tr_symmetry",
    )


def tr_homothety(scale: float, center: Point = (0.0, 0.0)) -> PolygonTransform:
    return PolygonTransform(
        transform=lambda polygon: as_polygon(map(lambda point: point_homothety(point, scale, center), polygon)),
        name="tr_homothety",
    )


def flt_convex_polygon() -> PolygonPredicate:
    def predicate(polygon: Polygon) -> bool:
        directions = tuple(
            cross(polygon[i], polygon[(i + 1) % len(polygon)], polygon[(i + 2) % len(polygon)])
            for i in range(len(polygon))
        )
        non_zero = tuple(value for value in directions if abs(value) > EPSILON)
        if not non_zero:
            return False
        return all(value > 0 for value in non_zero) or all(value < 0 for value in non_zero)

    return PolygonPredicate(predicate=predicate, name="flt_convex_polygon")


def flt_angle_point(point: Point) -> PolygonPredicate:
    return PolygonPredicate(predicate=lambda polygon: point in polygon, name="flt_angle_point")


def flt_square(max_area: float) -> PolygonPredicate:
    return PolygonPredicate(predicate=lambda polygon: polygon_area(polygon) < max_area, name="flt_square")


def flt_short_side(max_length: float) -> PolygonPredicate:
    return PolygonPredicate(
        predicate=lambda polygon: min_side_length(polygon) < max_length,
        name="flt_short_side",
    )


def flt_point_inside(point: Point) -> PolygonPredicate:
    return PolygonPredicate(
        predicate=lambda polygon: flt_convex_polygon().predicate(polygon) and point_in_convex_polygon(point, polygon),
        name="flt_point_inside",
    )


def flt_polygon_angles_inside(reference_polygon: Polygon) -> PolygonPredicate:
    vertices = tuple(reference_polygon)
    return PolygonPredicate(
        predicate=lambda polygon: flt_convex_polygon().predicate(polygon)
        and any(point_in_convex_polygon(vertex, polygon) for vertex in vertices),
        name="flt_polygon_angles_inside",
    )


def rectangle(origin: Point, width: float = 2.0, height: float = 1.0) -> Polygon:
    x, y = origin
    return as_polygon(((x, y), (x + width, y), (x + width, y + height), (x, y + height)))


def triangle(origin: Point, width: float = 2.0, height: float = 1.5) -> Polygon:
    x, y = origin
    return as_polygon(((x, y), (x + width, y), (x + width / 2, y + height)))


def hexagon(origin: Point, radius: float = 1.0) -> Polygon:
    x, y = origin
    return as_polygon(
        (
            (x + radius * math.cos(index * math.pi / 3), y + radius * math.sin(index * math.pi / 3))
            for index in range(6)
        )
    )


def _gen_linear(
    builder: Callable[..., Polygon],
    step: Point,
    start: Point = (0.0, 0.0),
    **kwargs,
) -> Iterator[Polygon]:
    return map(
        lambda index: builder((start[0] + step[0] * index, start[1] + step[1] * index), **kwargs),
        count(),
    )


def gen_rectangle(
    start: Point = (0.0, 0.0),
    step: Point = (3.0, 0.0),
    width: float = 2.0,
    height: float = 1.0,
) -> Iterator[Polygon]:
    return _gen_linear(rectangle, step=step, start=start, width=width, height=height)


def gen_triangle(
    start: Point = (0.0, 0.0),
    step: Point = (2.5, 0.0),
    width: float = 2.0,
    height: float = 1.5,
) -> Iterator[Polygon]:
    return _gen_linear(triangle, step=step, start=start, width=width, height=height)


def gen_hexagon(
    start: Point = (0.0, 0.0),
    step: Point = (2.3, 0.0),
    radius: float = 1.0,
) -> Iterator[Polygon]:
    return _gen_linear(hexagon, step=step, start=start, radius=radius)


def agr_origin_nearest(polygons: PolygonStream) -> Polygon:
    return reduce(
        lambda best, polygon: polygon
        if min(map(point_distance, polygon)) < min(map(point_distance, best))
        else best,
        polygons,
    )


def agr_max_side(polygons: PolygonStream) -> Polygon:
    return reduce(lambda best, polygon: polygon if max_side_length(polygon) > max_side_length(best) else best, polygons)


def agr_min_area(polygons: PolygonStream) -> Polygon:
    return reduce(lambda best, polygon: polygon if polygon_area(polygon) < polygon_area(best) else best, polygons)


def agr_perimeter(polygons: PolygonStream) -> float:
    return reduce(lambda acc, polygon: acc + polygon_perimeter(polygon), polygons, 0.0)


def agr_area(polygons: PolygonStream) -> float:
    return reduce(lambda acc, polygon: acc + polygon_area(polygon), polygons, 0.0)


def zip_tuple(*iterables: Iterable) -> Iterator[tuple]:
    return zip(*iterables)


def count_2d(rows: int | None = None, cols: int | None = None, start: Point = (0, 0)) -> Iterator[Point]:
    row_iter = count(start[0]) if rows is None else range(start[0], start[0] + rows)
    return (
        (row, col)
        for row in row_iter
        for col in (count(start[1]) if cols is None else range(start[1], start[1] + cols))
    )


def zip_polygons(*polygon_streams: PolygonStream) -> Iterator[Polygon]:
    return map(lambda polygons: as_polygon(chain.from_iterable(polygons)), zip(*polygon_streams))


def take(n: int, polygons: PolygonStream) -> tuple[Polygon, ...]:
    return tuple(islice(polygons, n))


def band(source: PolygonStream, *, angle: float = 0.0, offset: Point = (0.0, 0.0)) -> Iterator[Polygon]:
    rotated = map_polygons(tr_rotate(angle), source)
    return map_polygons(tr_translate(*offset), rotated)


def reject_intersecting(polygons: PolygonStream) -> Iterator[Polygon]:
    accepted: list[Polygon] = []
    for polygon in polygons:
        if not any(polygons_intersect(polygon, existing) for existing in accepted):
            accepted.append(polygon)
            yield polygon


def render_polygons_svg(
    polygons: Sequence[Polygon],
    target: str | Path,
    *,
    stroke: str = "#1f2937",
    fill_palette: Sequence[str] | None = None,
    width: int = 900,
    height: int = 500,
    padding: int = 32,
) -> Path:
    fill_palette = fill_palette or ("#93c5fd", "#86efac", "#fca5a5", "#fde68a", "#c4b5fd", "#f9a8d4")
    xs = tuple(x for polygon in polygons for x, _ in polygon)
    ys = tuple(y for polygon in polygons for _, y in polygon)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale_x = (width - 2 * padding) / max(max_x - min_x, 1.0)
    scale_y = (height - 2 * padding) / max(max_y - min_y, 1.0)
    scale = min(scale_x, scale_y)

    def project(point: Point) -> Point:
        x, y = point
        px = padding + (x - min_x) * scale
        py = height - padding - (y - min_y) * scale
        return (px, py)

    target_path = Path(target)
    polygons_markup = "\n".join(
        f'<polygon points="{" ".join(f"{px:.2f},{py:.2f}" for px, py in map(project, polygon))}" '
        f'fill="{fill_palette[index % len(fill_palette)]}" fill-opacity="0.45" '
        f'stroke="{stroke}" stroke-width="2" />'
        for index, polygon in enumerate(polygons)
    )
    target_path.write_text(
        "\n".join(
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<rect width="100%" height="100%" fill="#f8fafc" />',
                polygons_markup,
                "</svg>",
            )
        ),
        encoding="utf-8",
    )
    return target_path


def visualize_polygons(polygons: PolygonStream, target: str | Path, limit: int | None = None) -> Path:
    selected = tuple(polygons if limit is None else islice(polygons, limit))
    if not selected:
        raise ValueError("No polygons to visualize")
    return render_polygons_svg(selected, target)


def scenario_seven_each() -> dict[str, tuple[Polygon, ...]]:
    return {
        "rectangles": take(7, gen_rectangle()),
        "triangles": take(7, gen_triangle(start=(0.0, 3.0))),
        "hexagons": take(7, gen_hexagon(start=(0.0, 6.0))),
    }


def scenario_parallel_bands() -> tuple[Polygon, ...]:
    base = take(5, gen_rectangle())
    ribbons = (
        tuple(map_polygons(tr_translate(0.0, shift), band(iter(base), angle=math.pi / 7)))
        for shift in (0.0, 2.0, 4.0)
    )
    return tuple(chain.from_iterable(ribbons))


def scenario_crossed_bands() -> tuple[Polygon, ...]:
    first = take(8, band(gen_rectangle(start=(2.0, 1.0)), angle=math.pi / 8))
    second = take(8, band(gen_rectangle(start=(4.0, -2.0)), angle=math.pi / 2.8))
    return first + second


def scenario_symmetric_triangles() -> tuple[Polygon, ...]:
    top = take(6, band(gen_triangle(start=(0.0, 2.0)), angle=math.pi / 10))
    bottom = tuple(map_polygons(tr_symmetry("x"), iter(top)))
    return top + bottom


def scenario_scaled_quadrilaterals() -> tuple[Polygon, ...]:
    base = rectangle((1.6, 1.2), width=0.8, height=0.6)
    scales = map(lambda index: 0.6 + index * 0.35, range(1, 16))
    scaled = map(lambda scale: tr_homothety(scale)(base), scales)
    bounded = filter(
        lambda polygon: all(0.45 <= y / x <= 1.2 for x, y in polygon if abs(x) > EPSILON),
        scaled,
    )
    return tuple(bounded)


def scenario_filter_six() -> tuple[Polygon, ...]:
    source = scenario_parallel_bands()
    filtered = filter_polygons(flt_square(2.05), source)
    return tuple(islice(filtered, 6))


def scenario_short_side_selection() -> tuple[Polygon, ...]:
    source = scenario_scaled_quadrilaterals()
    filtered = filter_polygons(flt_short_side(1.5), source)
    return tuple(islice(filtered, 4))


def scenario_remove_intersections() -> tuple[Polygon, ...]:
    return tuple(reject_intersecting(scenario_crossed_bands()))


@tr_translate(1.0, 1.0)
def translated_rectangles() -> Iterator[Polygon]:
    return gen_rectangle()


@flt_short_side(1.8)
def compact_scaled_quadrilaterals() -> Iterator[Polygon]:
    return iter(scenario_scaled_quadrilaterals())


def demo_outputs(base_path: str | Path) -> dict[str, Path]:
    root = Path(base_path)
    root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "figure_2": visualize_polygons(chain.from_iterable(scenario_seven_each().values()), root / "figure_2.svg"),
        "parallel_bands": visualize_polygons(scenario_parallel_bands(), root / "parallel_bands.svg"),
        "crossed_bands": visualize_polygons(scenario_crossed_bands(), root / "crossed_bands.svg"),
        "symmetric_triangles": visualize_polygons(scenario_symmetric_triangles(), root / "symmetric_triangles.svg"),
        "scaled_quadrilaterals": visualize_polygons(scenario_scaled_quadrilaterals(), root / "scaled_quadrilaterals.svg"),
        "filter_six": visualize_polygons(scenario_filter_six(), root / "filter_six.svg"),
        "short_side_selection": visualize_polygons(
            scenario_short_side_selection(),
            root / "short_side_selection.svg",
        ),
        "remove_intersections": visualize_polygons(
            scenario_remove_intersections(),
            root / "remove_intersections.svg",
        ),
        "translated_rectangles": visualize_polygons(
            take(5, translated_rectangles()),
            root / "translated_rectangles.svg",
        ),
        "compact_scaled_quadrilaterals": visualize_polygons(
            take(4, compact_scaled_quadrilaterals()),
            root / "compact_scaled_quadrilaterals.svg",
        ),
    }
    return outputs


__all__ = [
    "Polygon",
    "PolygonStream",
    "agr_area",
    "agr_max_side",
    "agr_min_area",
    "agr_origin_nearest",
    "agr_perimeter",
    "band",
    "compact_scaled_quadrilaterals",
    "count_2d",
    "demo_outputs",
    "filter_polygons",
    "flt_angle_point",
    "flt_convex_polygon",
    "flt_point_inside",
    "flt_polygon_angles_inside",
    "flt_short_side",
    "flt_square",
    "gen_hexagon",
    "gen_rectangle",
    "gen_triangle",
    "map_polygons",
    "polygon_area",
    "polygon_centroid",
    "polygon_perimeter",
    "polygons_intersect",
    "reject_intersecting",
    "scenario_crossed_bands",
    "scenario_filter_six",
    "scenario_parallel_bands",
    "scenario_remove_intersections",
    "scenario_scaled_quadrilaterals",
    "scenario_seven_each",
    "scenario_short_side_selection",
    "scenario_symmetric_triangles",
    "take",
    "tr_homothety",
    "tr_rotate",
    "tr_symmetry",
    "tr_translate",
    "translated_rectangles",
    "visualize_polygons",
    "zip_polygons",
    "zip_tuple",
]
