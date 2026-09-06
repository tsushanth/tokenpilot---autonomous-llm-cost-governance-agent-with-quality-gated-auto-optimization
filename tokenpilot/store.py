"""Flat-JSON persistence: task definitions on disk, and run history under
./runs/. No database -- this is a single-user local CLI."""

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from tokenpilot.models import Task

DEFAULT_RUNS_DIR = Path("runs")


def load_task(path) -> Task:
    with open(path) as f:
        return Task.from_dict(json.load(f))


def save_run(task_name: str, record: dict, runs_dir: Path = DEFAULT_RUNS_DIR) -> tuple[str, Path]:
    task_dir = runs_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{task_name}-{stamp}-{uuid.uuid4().hex[:8]}"
    path = task_dir / f"{run_id}.json"

    payload = {"run_id": run_id, "task_name": task_name, **record}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=_json_default)

    return run_id, path


def list_runs(task_name: str = None, runs_dir: Path = DEFAULT_RUNS_DIR) -> list:
    if not runs_dir.exists():
        return []

    task_dirs = [runs_dir / task_name] if task_name else sorted(runs_dir.iterdir())
    records = []
    for task_dir in task_dirs:
        if not task_dir.is_dir():
            continue
        for run_file in sorted(task_dir.glob("*.json")):
            with open(run_file) as f:
                records.append(json.load(f))
    return records


def load_run(run_id: str, runs_dir: Path = DEFAULT_RUNS_DIR) -> dict:
    for run_file in runs_dir.glob(f"*/{run_id}.json"):
        with open(run_file) as f:
            return json.load(f)
    raise FileNotFoundError(f"No run found with id {run_id!r}")


def _json_default(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
