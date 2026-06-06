#!/usr/bin/env python3
"""Inspect an occupancy-map YAML/PGM and write machine-checkable artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

from .map_laser_sim import read_pgm
from .utils import load_yaml, write_json


def maybe_write_png(width: int, height: int, pixels: List[int], png_path: Path) -> bool:
    try:
        from PIL import Image
        img = Image.new("L", (width, height))
        img.putdata(pixels)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_path)
        return True
    except Exception:  # noqa: BLE001
        return False


def build_report(map_yaml: str, artifact_dir: str) -> dict:
    map_yaml_path = Path(map_yaml).resolve()
    data = load_yaml(map_yaml_path)
    image_path = map_yaml_path.parent / data["image"]
    width, height, maxval, pixels = read_pgm(str(image_path))
    occupied = sum(1 for p in pixels if p < 100)
    free = sum(1 for p in pixels if p > 240)
    unknown = len(pixels) - occupied - free
    png_path = Path(artifact_dir) / (map_yaml_path.stem + ".png")
    png_written = maybe_write_png(width, height, pixels, png_path)
    report = {
        "pass": width > 0 and height > 0 and occupied > 10 and free > 10,
        "map_yaml": str(map_yaml_path),
        "image": str(image_path),
        "png": str(png_path) if png_written else None,
        "width": width,
        "height": height,
        "maxval": maxval,
        "occupied_pixels": occupied,
        "free_pixels": free,
        "unknown_pixels": unknown,
        "resolution": data.get("resolution"),
        "origin": data.get("origin"),
    }
    write_json(Path(artifact_dir) / f"{map_yaml_path.stem}_map_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", dest="map_yaml", required=True)
    parser.add_argument("--artifact-dir", default="artifacts")
    args = parser.parse_args(argv)
    report = build_report(args.map_yaml, args.artifact_dir)
    print(report)


if __name__ == "__main__":
    main()
