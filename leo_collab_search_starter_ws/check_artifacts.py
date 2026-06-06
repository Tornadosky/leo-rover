#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

checks = [
    ("artifacts/collaborative_search_result.json", lambda d: d.get("pass") is True and d.get("target_found") is True),
    ("artifacts/semantic_map_latest.json", lambda d: d.get("object_count", 0) >= 1),
    ("artifacts/logical_robot_sim_latest.json", lambda d: d.get("pass") is True and "leo1" in d.get("robots", {})),
]

root = Path(__file__).resolve().parent
ok = True
for rel, pred in checks:
    p = root / rel
    if not p.exists():
        print(f"MISSING {rel}")
        ok = False
        continue
    data = json.loads(p.read_text())
    passed = bool(pred(data))
    print(f"{rel}: {'PASS' if passed else 'FAIL'}")
    ok = ok and passed
sys.exit(0 if ok else 1)
