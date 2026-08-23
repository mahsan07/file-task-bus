import tempfile
import unittest
from pathlib import Path

from file_task_bus import TaskBus
from file_task_bus.cli import main


class TaskBusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bus = TaskBus(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_happy_path(self):
        submitted = self.bus.submit("summarize", {"document": "notes.md"}, task_id="task-1")
        self.assertEqual("inbox", submitted["status"])
        claimed = self.bus.claim_next("researcher")
        self.assertEqual("task-1", claimed["id"])
        completed = self.bus.complete("task-1", {"summary": "done"}, "researcher")
        self.assertEqual("processed", completed["status"])
        self.assertEqual({"summary": "done"}, completed["result"])

    def test_approval_and_rejection_lanes(self):
        self.bus.submit("publish", task_id="task-2", requires_approval=True)
        self.bus.claim_next("writer")
        pending = self.bus.complete("task-2", {"draft": "ready"}, "writer")
        self.assertEqual("awaiting_approval", pending["status"])
        rejected = self.bus.reject("task-2", "editor", "citation missing")
        self.assertEqual("failed", rejected["status"])
        self.assertEqual("citation missing", rejected["error"])

    def test_invalid_transition_is_visible(self):
        self.bus.submit("not claimed", task_id="task-3")
        with self.assertRaisesRegex(ValueError, "current state: inbox"):
            self.bus.complete("task-3", {}, "worker")

    def test_digest_counts(self):
        self.bus.submit("one", task_id="one")
        self.bus.submit("two", task_id="two")
        self.bus.claim_next("worker")
        counts = self.bus.digest()["counts"]
        self.assertEqual(1, counts["inbox"])
        self.assertEqual(1, counts["processing"])

    def test_cli_failure_is_a_clean_parser_error(self):
        with self.assertRaises(SystemExit) as raised:
            main(["--root", self.temp.name, "complete", "missing", "--actor", "worker", "--result", "{}"])
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
