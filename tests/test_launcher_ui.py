from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO_ROOT = Path(__file__).resolve().parents[1]
for source_root in (REPO_ROOT / "app", REPO_ROOT / "ui" / "views"):
    value = str(source_root)
    if value in sys.path:
        sys.path.remove(value)
    sys.path.insert(0, value)

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
import launcher  # noqa: E402


class FakeResourceService:
    def get_device_requirements(self, device):
        result = [("sensevoice:model", "SenseVoice model")]
        if device == "cuda":
            result.append(("cuda:whisper", "CUDA runtime pack"))
        return result

    def validate_device(self, device):
        missing = [("sensevoice:model", "SenseVoice model")]
        return False, missing


class FakeMimeData:
    def __init__(self, paths):
        self._urls = [QUrl.fromLocalFile(path) for path in paths]

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return list(self._urls)


class FakeDropEvent:
    def __init__(self, paths):
        self._mime = FakeMimeData(paths)
        self.accepted = False

    def mimeData(self):
        return self._mime

    def acceptProposedAction(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


class LauncherUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_project_summary_maps_translation_review_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "phỏng_vấn_zh.mp4"
            video.write_bytes(b"fixture")
            with patch.object(launcher, "workspace_root", return_value=str(root)):
                state_path = Path(launcher._project_state_path(str(video)))
                state_path.parent.mkdir(parents=True)
                state = {
                    "input_language": "zh",
                    "steps": {"extract_audio": "done", "transcribe": "done", "translate_raw": "done"},
                    "segments": [{"id": "cue-1", "end": 78.2}],
                    "artifacts": {"translation_final": "translation/final.json"},
                }
                state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
                summary = launcher.project_card_summary(str(video))
                saved = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual("Cần duyệt", summary["status"])
        self.assertEqual(64, summary["progress"])
        self.assertIn("Tiếng Trung → Tiếng Việt", summary["facts"])
        self.assertIn("01:18", summary["facts"])
        self.assertEqual(state, saved)

    def test_exported_project_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "tutorial_en.mp4"
            video.write_bytes(b"fixture")
            with patch.object(launcher, "workspace_root", return_value=str(root)):
                state_path = Path(launcher._project_state_path(str(video)))
                state_path.parent.mkdir(parents=True)
                state_path.write_text(json.dumps({
                    "input_language": "en", "artifacts": {"final_video": "output/final.mp4"}
                }), encoding="utf-8")
                summary = launcher.project_card_summary(str(video))
        self.assertEqual("Đã xuất", summary["status"])
        self.assertEqual(100, summary["progress"])

    def test_launcher_exposes_approved_vietnamese_hierarchy_and_advisory(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(launcher, "workspace_root", return_value=tmp), \
                patch.object(launcher.LauncherWindow, "_start_hardware_probe", lambda _self: None), \
                patch.object(launcher.LauncherWindow, "_resource_service", return_value=FakeResourceService()):
            window = launcher.LauncherWindow()
            window._load_recent()
            window._validate_resources_for_device()
            self.app.processEvents()
            texts = [widget.text() for widget in window.findChildren(launcher.QLabel)]
            self.assertIn("Sẵn sàng trước khi chạy", texts)
            self.assertIn("Hybrid · mặc định", texts)
            self.assertIn("Dự án gần đây", texts)
            self.assertEqual("＋ Dự án mới", window.new_btn.text())
            self.assertTrue(window.new_btn.isEnabled())
            self.assertIn("cần xử lý", window._resource_badge.text())
            self.assertTrue(any(isinstance(window.grid.itemAt(i).widget(), launcher.DropProjectCard)
                                for i in range(window.grid.count())))
            window.close()

    def test_drop_uses_supported_local_video_and_rejects_other_files(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(launcher, "workspace_root", return_value=tmp), \
                patch.object(launcher.LauncherWindow, "_start_hardware_probe", lambda _self: None), \
                patch.object(launcher.LauncherWindow, "_resource_service", return_value=FakeResourceService()):
            video = Path(tmp) / "clip.MP4"
            text = Path(tmp) / "notes.txt"
            video.write_bytes(b"fixture")
            text.write_text("fixture", encoding="utf-8")
            window = launcher.LauncherWindow()
            window.accept = Mock()
            rejected = FakeDropEvent([str(text)])
            window.dropEvent(rejected)
            self.assertFalse(rejected.accepted)
            accepted = FakeDropEvent([str(text), str(video)])
            window.dropEvent(accepted)
            self.assertTrue(accepted.accepted)
            self.assertEqual(os.path.normpath(str(video)), window.selected_video)
            window.accept.assert_called_once_with()
            window.close()


if __name__ == "__main__":
    unittest.main()
