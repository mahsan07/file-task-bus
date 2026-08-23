"""Filesystem-backed task lifecycle with atomic lane transitions."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

LANES = ("inbox", "processing", "awaiting_approval", "processed", "failed")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskBus:
    """Coordinate producers, workers, and reviewers through plain JSON files."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def init(self) -> None:
        for lane in LANES:
            (self.root / lane).mkdir(parents=True, exist_ok=True)

    def submit(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        *,
        task_id: str | None = None,
        created_by: str = "human",
        requires_approval: bool = False,
    ) -> dict[str, Any]:
        self.init()
        task_id = task_id or uuid.uuid4().hex[:12]
        if not task_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("task_id may contain only letters, digits, hyphens, and underscores")
        if self.find(task_id):
            raise FileExistsError(f"task already exists: {task_id}")
        now = utc_now()
        task = {
            "schema_version": 1,
            "id": task_id,
            "title": title,
            "status": "inbox",
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "claimed_by": None,
            "requires_approval": requires_approval,
            "payload": payload or {},
            "result": None,
            "error": None,
            "events": [{"at": now, "event": "submitted", "actor": created_by}],
        }
        self._write_atomic(self.root / "inbox" / f"{task_id}.json", task, exclusive=True)
        return task

    def claim_next(self, worker: str) -> dict[str, Any] | None:
        self.init()
        for source in sorted((self.root / "inbox").glob("*.json")):
            target = self.root / "processing" / source.name
            try:
                source.rename(target)
            except (FileNotFoundError, FileExistsError, PermissionError):
                continue
            task = self._load(target)
            task["status"] = "processing"
            task["claimed_by"] = worker
            self._event(task, "claimed", worker)
            self._write_atomic(target, task)
            return task
        return None

    def complete(self, task_id: str, result: dict[str, Any], actor: str) -> dict[str, Any]:
        path = self._require(task_id, "processing")
        task = self._load(path)
        if task["requires_approval"]:
            task["result"] = result
            return self._transition(path, task, "awaiting_approval", "approval_requested", actor)
        task["result"] = result
        return self._transition(path, task, "processed", "completed", actor)

    def approve(self, task_id: str, reviewer: str) -> dict[str, Any]:
        path = self._require(task_id, "awaiting_approval")
        task = self._load(path)
        return self._transition(path, task, "processed", "approved", reviewer)

    def reject(self, task_id: str, reviewer: str, reason: str) -> dict[str, Any]:
        path = self._require(task_id, "awaiting_approval")
        task = self._load(path)
        task["error"] = reason
        return self._transition(path, task, "failed", "rejected", reviewer)

    def fail(self, task_id: str, error: str, actor: str) -> dict[str, Any]:
        path = self._require(task_id, "processing")
        task = self._load(path)
        task["error"] = error
        return self._transition(path, task, "failed", "failed", actor)

    def find(self, task_id: str) -> tuple[str, Path] | None:
        for lane in LANES:
            path = self.root / lane / f"{task_id}.json"
            if path.exists():
                return lane, path
        return None

    def list(self, lane: str | None = None) -> list[dict[str, Any]]:
        if lane is not None and lane not in LANES:
            raise ValueError(f"unknown lane: {lane}")
        lanes = (lane,) if lane else LANES
        records = []
        for name in lanes:
            records.extend(self._load(path) for path in sorted((self.root / name).glob("*.json")))
        return records

    def digest(self) -> dict[str, Any]:
        return {
            "generated_at": utc_now(),
            "root": str(self.root.resolve()),
            "counts": {lane: len(list((self.root / lane).glob("*.json"))) for lane in LANES},
        }

    def watch(self, interval: float = 1.0) -> Iterator[dict[str, Any]]:
        """Yield a digest whenever lane counts change."""
        previous: dict[str, int] | None = None
        while True:
            current = self.digest()
            if current["counts"] != previous:
                previous = current["counts"]
                yield current
            time.sleep(interval)

    def _require(self, task_id: str, lane: str) -> Path:
        path = self.root / lane / f"{task_id}.json"
        if not path.exists():
            found = self.find(task_id)
            state = found[0] if found else "missing"
            raise ValueError(f"task {task_id} must be in {lane}; current state: {state}")
        return path

    def _transition(
        self, source: Path, task: dict[str, Any], lane: str, event: str, actor: str
    ) -> dict[str, Any]:
        target = self.root / lane / source.name
        source.rename(target)
        task["status"] = lane
        self._event(task, event, actor)
        self._write_atomic(target, task)
        return task

    @staticmethod
    def _event(task: dict[str, Any], event: str, actor: str) -> None:
        now = utc_now()
        task["updated_at"] = now
        task["events"].append({"at": now, "event": event, "actor": actor})

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_atomic(path: Path, value: dict[str, Any], exclusive: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if exclusive and path.exists():
            raise FileExistsError(path)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if exclusive and path.exists():
            temporary.unlink(missing_ok=True)
            raise FileExistsError(path)
        os.replace(temporary, path)
