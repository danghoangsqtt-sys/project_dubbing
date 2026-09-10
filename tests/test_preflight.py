from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import preflight


class PreflightTests(unittest.TestCase):
    def test_windows_release_name_uses_build_boundary(self) -> None:
        self.assertEqual("Windows 11", preflight.windows_release_name("26100"))
        self.assertEqual("Windows 10", preflight.windows_release_name("19045"))

    def test_aggregate_status_keeps_warnings_non_fatal(self) -> None:
        status, counts = preflight.aggregate_status(
            [
                preflight.check("ready", "pass", "ready"),
                preflight.check("models", "warning", "not installed"),
            ]
        )
        self.assertEqual("pass", status)
        self.assertEqual({"pass": 1, "warning": 1, "fail": 0}, counts)

    def test_aggregate_status_fails_on_required_check(self) -> None:
        status, counts = preflight.aggregate_status(
            [preflight.check("python", "fail", "wrong version")]
        )
        self.assertEqual("fail", status)
        self.assertEqual(1, counts["fail"])

    def test_run_command_does_not_use_shell(self) -> None:
        with patch("tools.preflight.subprocess.run") as mocked:
            mocked.return_value.returncode = 0
            mocked.return_value.stdout = "ok\n"
            mocked.return_value.stderr = ""
            code, stdout, _ = preflight.run_command(["tool", "argument"])
        self.assertEqual(0, code)
        self.assertEqual("ok", stdout)
        self.assertFalse(mocked.call_args.kwargs["shell"])
        self.assertEqual(["tool", "argument"], mocked.call_args.args[0])

    def test_resource_inventory_reports_missing_without_failure(self) -> None:
        with patch.object(preflight, "REPO_ROOT", Path("Z:/path-that-does-not-exist")):
            result = preflight.resource_check()
        self.assertEqual("warning", result["status"])
        self.assertTrue(all(item["status"] == "missing" for item in result["details"]["resources"]))

    def test_report_write_is_valid_json_and_leaves_no_temporary_file(self) -> None:
        report = {"schema_version": 1, "overall_status": "pass", "text": "Tiếng Việt"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            preflight.write_report(path, report)
            self.assertEqual(report, json.loads(path.read_text(encoding="utf-8")))
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_video_check_fails_for_missing_path(self) -> None:
        result = preflight.video_check(Path("missing-video.mp4"))
        self.assertEqual("fail", result["status"])
        self.assertIn("does not exist", result["summary"])


if __name__ == "__main__":
    unittest.main()
