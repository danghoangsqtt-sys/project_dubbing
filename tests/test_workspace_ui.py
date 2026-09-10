from __future__ import annotations

import ast
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO_ROOT = Path(__file__).resolve().parents[1]
for source_root in (REPO_ROOT / "app", REPO_ROOT / "ui"):
    value = str(source_root)
    if value in sys.path:
        sys.path.remove(value)
    sys.path.insert(0, value)

# App and UI both expose a top-level ``utils`` package. Test discovery may
# cache the app package before this module is imported, while UI views require
# ``ui/utils``. Existing imported app modules retain their own references.
cached_utils = sys.modules.get("utils")
cached_utils_file = Path(getattr(cached_utils, "__file__", "") or ".").resolve()
ui_root = (REPO_ROOT / "ui").resolve()
if cached_utils is not None and ui_root not in cached_utils_file.parents:
    for module_name in [name for name in sys.modules if name == "utils" or name.startswith("utils.")]:
        sys.modules.pop(module_name, None)

from PySide6.QtWidgets import QApplication  # noqa: E402
from controllers.pipeline_controller import PipelineController  # noqa: E402
from views.main_window import workspace_navigation_target  # noqa: E402
from views.start_panel import WORKSPACE_STAGES, workspace_stage_summary  # noqa: E402
from widgets.progress_dialog import PipelineProgressDialog  # noqa: E402


class _FakeButton:
    def __init__(self):
        self.enabled = True
        self.text = ""

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)

    def setText(self, text):
        self.text = str(text)


class _FakeProgressBar:
    def __init__(self):
        self.minimum = 0
        self.maximum = 100
        self.value = 0

    def setRange(self, minimum, maximum):
        self.minimum = int(minimum)
        self.maximum = int(maximum)

    def setValue(self, value):
        self.value = int(value)


class _CooperativeThread:
    def __init__(self):
        self.stop_called = False
        self.interruption_requested = False
        self.quit_called = False
        self.wait_timeout = None

    def stop(self):
        self.stop_called = True

    def isRunning(self):
        return True

    def requestInterruption(self):
        self.interruption_requested = True

    def quit(self):
        self.quit_called = True

    def wait(self, timeout):
        self.wait_timeout = timeout
        return True


class _FakeGui:
    def __init__(self, steps):
        self.current_project_state = SimpleNamespace(steps=dict(steps))
        self.voice_thread = _CooperativeThread()
        self._pipeline_active = True
        self._pipeline_step = "voiceover"
        self.run_all_btn = _FakeButton()
        self.progress_bar = _FakeProgressBar()
        self.refresh_count = 0
        self.logs = []

    def update_project_step(self, step_name, status):
        self.current_project_state.steps[step_name] = status

    def refresh_ui_state(self):
        self.refresh_count += 1

    def log(self, message):
        self.logs.append(str(message))


def _method_source(path: Path, class_name: str, method_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                    return ast.get_source_segment(source, member) or ""
    raise AssertionError(f"Không tìm thấy {class_name}.{method_name}")


class WorkspaceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_stage_summary_exposes_five_approved_vietnamese_stages(self):
        summary = workspace_stage_summary(has_video=False)
        self.assertEqual(5, len(summary["items"]))
        self.assertEqual(
            ["Chuẩn bị media", "Chép lời", "Dịch & kiểm duyệt", "Tạo giọng", "Trộn & xuất"],
            [item["label"] for item in summary["items"]],
        )
        self.assertEqual(["prepare", "transcript", "translate", "tts", "export"],
                         [item["key"] for item in summary["items"]])
        self.assertEqual(100, sum(weight for _key, _label, weight in WORKSPACE_STAGES))

    def test_stage_summary_maps_running_review_and_persisted_resume_states(self):
        running = workspace_stage_summary(
            has_video=True,
            segments=[{"id": "cue-1"}],
            translated_segments=[{"id": "cue-1", "qa_flags": ["number"]}],
            steps={"translate_raw": "done", "generate_tts": "running"},
            pipeline_active=True,
            pipeline_step="voiceover",
        )
        states = {item["key"]: item for item in running["items"]}
        self.assertEqual("review", states["translate"]["state"])
        self.assertEqual("● 1 vấn đề", states["translate"]["status"])
        self.assertEqual("running", states["tts"]["state"])
        self.assertEqual(73, running["progress"])

        stopped = workspace_stage_summary(
            has_video=True,
            segments=[{"id": "cue-1"}],
            steps={"translate_raw": "cancelled"},
        )
        stopped_states = {item["key"]: item["state"] for item in stopped["items"]}
        self.assertEqual("cancelled", stopped_states["translate"])
        self.assertTrue(stopped["resume_available"])

        failed = workspace_stage_summary(
            has_video=True,
            segments=[{"id": "cue-1"}],
            steps={"generate_tts": "failed"},
        )
        self.assertEqual("error", {item["key"]: item["state"] for item in failed["items"]}["tts"])
        self.assertTrue(failed["resume_available"])

    def test_subtitle_only_completion_counts_explicit_tts_skip(self):
        summary = workspace_stage_summary(
            has_video=True,
            segments=[{"id": "cue-1"}],
            translated_segments=[{"id": "cue-1"}],
            steps={"translate_raw": "done", "export": "done"},
            artifacts={"final_video": "output/final.mp4"},
            tts_skipped=True,
        )
        states = {item["key"]: item for item in summary["items"]}
        self.assertEqual("● Bỏ qua", states["tts"]["status"])
        self.assertEqual(100, summary["progress"])

    def test_header_navigation_targets_the_existing_workspace_pages(self):
        self.assertEqual(("page", 0), workspace_navigation_target("studio"))
        self.assertEqual(("page", 2), workspace_navigation_target("translation"))
        self.assertEqual(("page", 3), workspace_navigation_target("voice"))
        self.assertEqual(("resources", None), workspace_navigation_target("resources"))
        self.assertEqual(("page", 0), workspace_navigation_target("unknown"))

    def test_stop_is_cooperative_and_preserves_completed_steps(self):
        gui = _FakeGui({"transcribe": "done", "generate_tts": "running"})
        worker = gui.voice_thread
        controller = PipelineController(gui)

        controller._on_pipeline_stop()

        self.assertTrue(worker.stop_called)
        self.assertTrue(worker.interruption_requested)
        self.assertTrue(worker.quit_called)
        self.assertEqual(1500, worker.wait_timeout)
        self.assertIsNone(gui.voice_thread)
        self.assertEqual("done", gui.current_project_state.steps["transcribe"])
        self.assertEqual("cancelled", gui.current_project_state.steps["generate_tts"])
        self.assertFalse(gui._pipeline_active)
        self.assertEqual("", gui._pipeline_step)
        self.assertEqual("Tạo tiếp", gui.run_all_btn.text)
        self.assertEqual(1, gui.refresh_count)

    def test_failure_persists_running_stage_for_resume(self):
        gui = _FakeGui({"transcribe": "done", "generate_tts": "running"})
        gui.voice_thread = None
        controller = PipelineController(gui)

        controller.pipeline_fail("fixture failure")

        self.assertEqual("done", gui.current_project_state.steps["transcribe"])
        self.assertEqual("failed", gui.current_project_state.steps["generate_tts"])
        self.assertFalse(gui._pipeline_active)
        self.assertEqual("", gui._pipeline_step)
        self.assertEqual(1, gui.refresh_count)

    def test_normal_thread_paths_do_not_force_qthread_termination(self):
        controller_source = _method_source(
            REPO_ROOT / "ui" / "controllers" / "pipeline_controller.py",
            "PipelineController",
            "_on_pipeline_stop",
        )
        voice_source = _method_source(
            REPO_ROOT / "ui" / "main_window.py",
            "VideoTranslatorGUI",
            "run_voiceover_with_progress",
        )
        self.assertNotIn(".terminate(", controller_source)
        self.assertNotIn(".terminate(", voice_source)

    def test_progress_dialog_can_hide_without_stopping_elapsed_tracking(self):
        dialog = PipelineProgressDialog()
        dialog.add_step("ai_process", "Xử lý phụ đề bằng AI")
        dialog.show()
        self.app.processEvents()
        dialog.start_step("ai_process")
        started_at = dialog.workflow_start_time
        dialog.hide()
        self.app.processEvents()

        self.assertEqual(started_at, dialog.workflow_start_time)
        self.assertTrue(dialog.total_timer.isActive())
        self.assertEqual("Đang chạy", dialog.steps["ai_process"].status_label.text())

        dialog.cancel_step("ai_process")
        self.assertEqual("cancelled", dialog.steps["ai_process"].status)
        self.assertEqual("Đã dừng", dialog.steps["ai_process"].status_label.text())
        dialog.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
