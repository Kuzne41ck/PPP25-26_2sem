from __future__ import annotations

from itertools import islice
from pathlib import Path

from functional_polygons import (
    agr_area,
    agr_max_side,
    agr_min_area,
    agr_origin_nearest,
    agr_perimeter,
    demo_outputs,
    gen_hexagon,
    gen_rectangle,
    gen_triangle,
    take,
    zip_polygons,
)


def main() -> None:
    root = Path(__file__).resolve().parent
    output_dir = root / "artifacts"
    outputs = demo_outputs(output_dir)

    sample = take(5, gen_rectangle()) + take(5, gen_triangle(start=(0, 3))) + take(5, gen_hexagon(start=(0, 6)))
    print("Generated files:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")

    print("\nAggregations:")
    print(f"  Total area: {agr_area(iter(sample)):.3f}")
    print(f"  Total perimeter: {agr_perimeter(iter(sample)):.3f}")
    print(f"  Max side polygon vertices: {agr_max_side(iter(sample))}")
    print(f"  Min area polygon vertices: {agr_min_area(iter(sample))}")
    print(f"  Nearest to origin polygon vertices: {agr_origin_nearest(iter(sample))}")

    zipped = tuple(islice(zip_polygons(gen_rectangle(), gen_triangle(start=(0, 3))), 2))
    print("\nzip_polygons sample:")
    for polygon in zipped:
        print(f"  {polygon}")


if __name__ == "__main__":
    main()
