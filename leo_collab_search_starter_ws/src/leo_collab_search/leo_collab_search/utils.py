"""Small utilities shared by the collaborative-search starter nodes.

The package intentionally uses simple JSON-on-std_msgs/String interfaces for the
first MVP. That keeps Codex and the team away from custom message-generation
issues until the demo logic is stable.
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


def load_yaml(path: str | os.PathLike[str]) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def write_json(path: str | os.PathLike[str], payload: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    tmp.replace(p)


def now_sec() -> float:
    return time.time()


def parse_robot_names(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip(" /") for v in value if str(v).strip(" /")]
    if value is None:
        return []
    return [v.strip(" /") for v in str(value).split(",") if v.strip(" /")]


def yaw_to_quat(yaw: float) -> Tuple[float, float, float, float]:
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


def quat_to_yaw(x: float, y: float, z: float, w: float) -> float:
    # ROS standard yaw extraction.
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def angle_wrap(a: float) -> float:
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def dist2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def ensure_artifact_dir(path: str) -> str:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


@dataclass
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0

    @classmethod
    def from_any(cls, value: Any) -> "Pose2D":
        if isinstance(value, dict):
            return cls(float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("yaw", 0.0)))
        if isinstance(value, (list, tuple)):
            x = float(value[0]) if len(value) > 0 else 0.0
            y = float(value[1]) if len(value) > 1 else 0.0
            yaw = float(value[2]) if len(value) > 2 else 0.0
            return cls(x, y, yaw)
        return cls(0.0, 0.0, 0.0)

    def as_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "yaw": self.yaw}


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
