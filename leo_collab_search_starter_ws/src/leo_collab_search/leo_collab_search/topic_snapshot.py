#!/usr/bin/env python3
"""Write a ROS graph topic snapshot as JSON for milestone checks."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .utils import write_json


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default="artifacts")
    parser.add_argument("--name", default="topic_snapshot")
    parser.add_argument("--required", default="")
    args = parser.parse_args(argv)
    required = [t.strip() for t in args.required.split(",") if t.strip()]
    result = subprocess.run(["ros2", "topic", "list"], text=True, capture_output=True, check=False)
    topics = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    missing = [t for t in required if t not in topics]
    payload = {
        "pass": result.returncode == 0 and not missing,
        "returncode": result.returncode,
        "topics": topics,
        "required": required,
        "missing": missing,
        "stderr": result.stderr,
    }
    write_json(Path(args.artifact_dir) / f"{args.name}.json", payload)
    print(payload)


if __name__ == "__main__":
    main()
