"""Run the complete task lifecycle without shell-specific JSON quoting."""

import json
import tempfile
from pathlib import Path

from file_task_bus import TaskBus

with tempfile.TemporaryDirectory() as temporary:
    bus = TaskBus(Path(temporary) / "bus")
    submitted = bus.submit(
        "Summarize the meeting",
        {"source": "meeting-notes.md"},
        task_id="demo-task",
        requires_approval=True,
    )
    claimed = bus.claim_next("local-agent")
    pending = bus.complete(claimed["id"], {"summary": "Decisions captured"}, "local-agent")
    approved = bus.approve(pending["id"], "human")
    print(json.dumps({"submitted": submitted["status"], "claimed": claimed["status"],
                      "pending": pending["status"], "final": approved["status"],
                      "digest": bus.digest()["counts"]}, indent=2))
