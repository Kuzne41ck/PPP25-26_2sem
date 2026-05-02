# Функциональный API для работы с полигонами

Проект реализует ленивый API для генерации, преобразования, фильтрации, агрегации и визуализации плоских полигонов в функциональном стиле.

## План реализации

1. Описать единый формат данных: полигон как `tuple[tuple[float, float], ...]`, поток полигонов как итератор.
2. Вынести геометрическое ядро в чистые функции: площадь, периметр, стороны, пересечения, принадлежность точки.
3. Реализовать генераторы бесконечных последовательностей через `itertools.count`, `map`, `islice`.
4. Реализовать трансформации и фильтры как вызываемые объекты, которые работают и в `map`/`filter`, и как декораторы.
5. Добавить агрегирующие функции через `functools.reduce`.
6. Добавить утилиты `zip_polygons`, `count_2d`, `zip_tuple`.
7. Собрать сценарии из задания и сохранить визуализации в SVG.

## Что реализовано

- Визуализация последовательностей полигонов через `matplotlib` (`matplotlib.patches.Polygon`).
- Бесконечные генераторы:
  - `gen_rectangle`
  - `gen_triangle`
  - `gen_hexagon`
- Трансформации:
  - `tr_translate`
  - `tr_rotate`
  - `tr_symmetry`
  - `tr_homothety`
- Все 6 фильтров:
  - `flt_convex_polygon`
  - `flt_angle_point`
  - `flt_square`
  - `flt_short_side`
  - `flt_point_inside`
  - `flt_polygon_angles_inside`
- Все 3 сценария применения фильтров.
- Декораторы на основе трансформаций и фильтров.
- Все 5 агрегирующих функций:
  - `agr_origin_nearest`
  - `agr_max_side`
  - `agr_min_area`
  - `agr_perimeter`
  - `agr_area`
- Утилиты:
  - `zip_polygons`
  - `count_2d`
  - `zip_tuple`

## Запуск из терминала

Сначала установите зависимость:

```bash
python -m pip install matplotlib
```

Показать список сценариев:

```bash
python main.py list --verbose
```

Открыть окно с рисунком:

```bash
python main.py show parallel_bands
```

Открыть окно и одновременно сохранить PNG:

```bash
python main.py show crossed_bands --save artifacts/crossed_bands.png
```

Сохранить без открытия окна:

```bash
python main.py save symmetric_triangles artifacts/symmetric_triangles.png
```

Выгрузить все готовые сценарии:

```bash
python main.py export-all --dir artifacts
```

## Альтернативный запуск

```bash
python demo.py
```

Для запуска без открытия окон `matplotlib`:

```bash
python demo.py --no-show
```
