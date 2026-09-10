import hashlib
import math
import os
import json
import time
import shutil
import re
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from runtime_paths import asset_path, subprocess_hidden_kwargs, workspace_root


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
PIPELINE_STAGES = (
    "extract_audio", "transcribe", "translate_raw", "refine_translation",
    "separate_audio", "generate_tts", "build_subtitle", "mix_audio", "export",
)


def _project_state_path(video_path: str) -> str:
    name = os.path.splitext(os.path.basename(video_path))[0] or "project"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower() or "project"
    digest = hashlib.sha1(os.path.abspath(video_path).encode("utf-8")).hexdigest()[:8]
    return os.path.join(workspace_root(), "projects", f"{slug}_{digest}", "project.json")


def _read_project_state(video_path: str) -> dict:
    try:
        with open(os.path.normpath(_project_state_path(video_path)), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _format_duration(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def project_card_summary(video_path: str) -> dict:
    """Build read-only, deterministic launcher state for one recent project."""
    state = _read_project_state(video_path)
    artifacts = dict(state.get("artifacts") or {})
    steps = dict(state.get("steps") or {})
    segments = list(state.get("segments") or state.get("current_segments") or [])
    completed = sum(1 for stage in PIPELINE_STAGES if str(steps.get(stage, "")).lower() == "done")
    progress = int(round((completed / len(PIPELINE_STAGES)) * 100)) if state else 0
    status = "Sẵn sàng"
    tone = "neutral"
    resume = "Bắt đầu xử lý"
    if artifacts.get("final_video") or str(steps.get("export", "")).lower() == "done":
        status, tone, progress, resume = "Đã xuất", "done", 100, "MP4 + SRT + báo cáo"
    elif artifacts.get("voice_vi") or artifacts.get("mixed_vi") or str(steps.get("generate_tts", "")).lower() == "done":
        status, tone, progress, resume = "Cần duyệt", "warning", max(progress, 82), "Đang ở: Duyệt lồng tiếng"
    elif artifacts.get("translation_final") or str(steps.get("translate_raw", "")).lower() == "done":
        status, tone, progress, resume = "Cần duyệt", "warning", max(progress, 64), "Đang ở: Duyệt bản dịch"
    elif artifacts.get("transcript_segments") or str(steps.get("transcribe", "")).lower() == "done":
        status, tone, progress, resume = "Đã chép lời", "info", max(progress, 42), "Đang ở: Chép lời"

    language = str(state.get("input_language") or "").strip().lower()
    source_label = {"zh": "Tiếng Trung", "en": "Tiếng Anh"}.get(language, "Chưa chọn ngôn ngữ")
    duration = max(
        (float(item.get("end", item.get("end_time", 0.0)) or 0.0) for item in segments if isinstance(item, dict)),
        default=0.0,
    )
    facts = [f"{source_label} → Tiếng Việt"]
    if duration > 0:
        facts.append(_format_duration(duration))
    if segments:
        facts.append(f"{len(segments)} cues")
    return {
        "name": os.path.basename(video_path),
        "status": status,
        "tone": tone,
        "progress": max(0, min(100, progress)),
        "resume": resume,
        "facts": " · ".join(facts),
    }


def is_supported_video_path(path: str) -> bool:
    return bool(path and os.path.isfile(path) and Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS)



def _recent_projects_path():
    # ``__file__`` lives inside ``_internal`` in a frozen build. Recent
    # project data belongs beside the executable, not inside bundled assets.
    return os.path.join(workspace_root(), "recent_projects.json")


def _load_recent_projects(settings=None):
    path = _recent_projects_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_recent_projects(settings, projects):
    path = _recent_projects_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def _project_pipeline_status(video_path: str) -> tuple[str, str]:
    """Read the persisted project stage without creating or modifying it."""
    summary = project_card_summary(video_path)
    colors = {"done": "#54d18b", "warning": "#ffd400", "info": "#8ad7ff", "neutral": "#8394aa"}
    return summary["status"], colors[summary["tone"]]


def _extract_thumbnail(video_path: str, output_path: str) -> str:
    if not os.path.exists(video_path):
        return ""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    import subprocess
    try:
        subprocess.run(
            [_ffmpeg_path(), "-y", "-i", video_path, "-vframes", "1", "-q:v", "3",
             "-vf", "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2",
             output_path],
            capture_output=True, timeout=30, **subprocess_hidden_kwargs(),
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception:
        pass
    return ""


def _ffmpeg_path():
    from runtime_paths import bin_path
    return os.path.join(bin_path(), "ffmpeg", "ffmpeg.exe")


def _get_video_duration(video_path: str) -> float:
    try:
        import subprocess
        ffprobe = _ffmpeg_path().replace("ffmpeg.exe", "ffprobe.exe")
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=30, **subprocess_hidden_kwargs(),
        )
        if result.returncode == 0:
            return float(result.stdout.strip() or 0)
    except Exception:
        pass
    return 0.0


MSG_STYLE = """
    QMessageBox { background-color: #0f1724; }
    QLabel { color: #ffffff; }
    QPushButton { background-color: #22344d; color: #f8fbff; border: 1px solid #34506f;
        border-radius: 8px; padding: 6px 16px; font-weight: 600; }
    QPushButton:hover { background-color: #29405d; }
"""


class ProjectCard(QFrame):
    def __init__(self, video_path: str, thumbnail_cache_dir: str, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self._orig_pixmap = None
        summary = project_card_summary(video_path)
        self.setObjectName("projectCard")
        self.setMinimumSize(260, 245)
        self.setMaximumWidth(460)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(f"Mở lại dự án {summary['name']}, {summary['status']}")
        self.setStyleSheet(
            "#projectCard { background:#121b2b; border:1px solid #263850; border-radius:10px; }"
            "#projectCard:hover, #projectCard:focus { border:2px solid #4ed0b3; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.thumb_label = QLabel()
        self.thumb_label.setMinimumSize(220, 120)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(
            "background-color:#0b1320; color:#8196ad; border:1px solid #30445d; border-radius:6px;"
        )
        self.thumb_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.thumb_label)

        name_row = QHBoxLayout()
        self.name_label = QLabel(summary["name"])
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(36)
        self.name_label.setStyleSheet("color:#f8fbff; font-size:12px; font-weight:700;")
        name_row.addWidget(self.name_label, 1)

        _stage_text, stage_color = _project_pipeline_status(video_path)
        self.stage_badge = QLabel(f"● {summary['status']}")
        self.stage_badge.setAlignment(Qt.AlignCenter)
        self.stage_badge.setStyleSheet(
            f"background-color:#142437; color:{stage_color}; border:1px solid #2e4b68; "
            "border-radius:9px; padding:3px 8px; font-size:10px; font-weight:700;"
        )
        name_row.addWidget(self.stage_badge)
        layout.addLayout(name_row)

        self.facts_label = QLabel(summary["facts"])
        self.facts_label.setStyleSheet("color:#9bb2ca; font-size:10px;")
        layout.addWidget(self.facts_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(summary["progress"])
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            "QProgressBar{background:#09111e;border:0;border-radius:3px;}"
            "QProgressBar::chunk{background:#4ed0b3;border-radius:3px;}"
        )
        layout.addWidget(self.progress_bar)
        progress_row = QHBoxLayout()
        resume_label = QLabel(summary["resume"])
        resume_label.setStyleSheet("color:#8ad7ff; font-size:10px;")
        progress_label = QLabel(f"{summary['progress']}%")
        progress_label.setStyleSheet("color:#9bb2ca; font-size:10px;")
        progress_row.addWidget(resume_label, 1)
        progress_row.addWidget(progress_label)
        layout.addLayout(progress_row)

        self._load_thumb(thumbnail_cache_dir)

    def _load_thumb(self, cache_dir):
        thumb_path = os.path.join(cache_dir, _thumbnail_name(self.video_path))
        if os.path.exists(thumb_path):
            self._orig_pixmap = QPixmap(thumb_path)
            self._update_thumb()
        else:
            self.thumb_label.setText("Xem trước sẽ được tạo khi mở dự án")

    def _update_thumb(self):
        if self._orig_pixmap is None or self._orig_pixmap.isNull():
            return
        w = self.thumb_label.width()
        if w > 0:
            self.thumb_label.setPixmap(self._orig_pixmap.scaled(w, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_thumb()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            event.ignore()
            return
        self.window().selected_video = self.video_path
        self.window().accept()


class DropProjectCard(QFrame):
    def __init__(self, launcher, parent=None):
        super().__init__(parent)
        self.launcher = launcher
        self.setObjectName("dropProjectCard")
        self.setMinimumSize(260, 245)
        self.setMaximumWidth(460)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Kéo video vào đây hoặc nhấn để chọn video")
        self.setStyleSheet(
            "#dropProjectCard{background:#121b2b;border:1px dashed #36516e;border-radius:10px;}"
            "#dropProjectCard:hover,#dropProjectCard:focus{border:2px solid #4ed0b3;}"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        mark = QLabel("＋")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(44, 44)
        mark.setStyleSheet("background:#72d7ea;color:#08111f;border-radius:10px;font-size:22px;font-weight:800;")
        title = QLabel("Kéo video vào đây")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:#ffffff;font-size:15px;font-weight:800;")
        hint = QLabel("MP4, MKV, AVI, MOV, WEBM · dữ liệu giữ trên máy")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8ad7ff;font-size:10px;")
        layout.addWidget(mark, 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(hint)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.launcher._on_new_project()
            event.accept()
            return
        super().mousePressEvent(event)


def _extract_waveform_audio(video_path: str, temp_root: str) -> str:
    video_hash = hashlib.md5(video_path.encode("utf-8")).hexdigest()[:12]
    audio_path = os.path.join(temp_root, f"waveform_{video_hash}.wav")
    if os.path.exists(audio_path):
        return audio_path
    if not os.path.exists(video_path):
        return ""
    os.makedirs(os.path.dirname(audio_path) or ".", exist_ok=True)
    import subprocess
    try:
        subprocess.run(
            [_ffmpeg_path(), "-y", "-loglevel", "error", "-i", video_path,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
            check=True, timeout=60, **subprocess_hidden_kwargs(),
        )
        print(f"[Launcher] Waveform audio extracted: {audio_path}")
    except Exception as exc:
        print(f"[Launcher] Waveform extract failed: {exc}")
        return ""
    return audio_path if os.path.exists(audio_path) else ""


def _prepare_timeline_visual_cache(video_path: str, temp_root: str) -> None:
    """Build the editor's static V1/A1 cache before opening the editor."""
    try:
        import numpy as np
        import subprocess
        import wave

        source = os.path.abspath(video_path)
        stat = os.stat(source)
        digest = hashlib.md5(source.encode("utf-8")).hexdigest()[:12]
        cache_dir = os.path.join(temp_root, "timeline_visuals")
        thumb_dir = os.path.join(temp_root, "timeline_thumbnails")
        manifest_path = os.path.join(cache_dir, f"{digest}.json")
        os.makedirs(cache_dir, exist_ok=True)

        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if (
                int(existing.get("visual_version", 0)) == 4
                and
                existing.get("source") == source
                and existing.get("size") == int(stat.st_size)
                and existing.get("mtime_ns") == int(stat.st_mtime_ns)
                and existing.get("waveform")
                and all(os.path.exists(path) for _time, path in existing.get("thumbnails", []))
            ):
                print("[Launcher] Timeline visuals loaded from cache")
                return
        except (OSError, ValueError, TypeError):
            pass

        duration_s = _get_video_duration(source)
        if duration_s <= 60.0:
            interval_s = max(2.0, duration_s / 12.0)
        elif duration_s <= 300.0:
            interval_s = max(5.0, duration_s / 30.0)
        else:
            interval_s = max(20.0, duration_s / 90.0)
        thumb_count = max(1, min(120, int(math.ceil(duration_s / interval_s))))
        timestamps = [0.0] if duration_s <= 1.0 else [
            min(duration_s - 0.05, index * interval_s) for index in range(thumb_count)
        ]
        os.makedirs(thumb_dir, exist_ok=True)

        def build_waveform():
            waveform = []
            audio_path = _extract_waveform_audio(source, temp_root)
            waveform_duration = duration_s
            if audio_path and os.path.exists(audio_path):
                with wave.open(audio_path, "rb") as audio_file:
                    frame_count = audio_file.getnframes()
                    sample_rate = max(1, audio_file.getframerate())
                    raw_samples = audio_file.readframes(frame_count)
                samples = np.frombuffer(raw_samples, dtype=np.int16).astype(np.float32)
                waveform_duration = max(waveform_duration, frame_count / sample_rate)
                peak = float(np.max(np.abs(samples))) if samples.size else 0.0
                if peak > 0:
                    samples /= peak
                    bucket_count = int(min(1200, max(240, round(waveform_duration * 12.0))))
                    chunk_size = max(256, int(np.ceil(samples.size / max(1, bucket_count))))
                    for start in range(0, samples.size, chunk_size):
                        chunk = samples[start:start + chunk_size]
                        peak_value = float(np.max(np.abs(chunk))) if chunk.size else 0.0
                        rms_value = float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0
                        waveform.append(min(1.0, max(0.03, max(peak_value, rms_value * 1.15) ** 0.85)))
            return waveform, waveform_duration

        def build_thumbnail(index_and_time):
            index, timestamp_s = index_and_time
            output_path = os.path.join(thumb_dir, f"launcher_{digest}_v4_{index:03d}.jpg")
            if not os.path.exists(output_path):
                subprocess.run(
                    [_ffmpeg_path(), "-y", "-loglevel", "error", "-ss", f"{timestamp_s:.3f}",
                     "-i", source, "-frames:v", "1", "-q:v", "4",
                     "-vf", "scale=180:-1:force_original_aspect_ratio=decrease", output_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=20,
                    **subprocess_hidden_kwargs(),
                )
            return [float(timestamp_s), output_path] if os.path.exists(output_path) and os.path.getsize(output_path) > 0 else None

        # Two independent FFmpeg workers seek the original video directly,
        # while waveform extraction runs alongside them. This stays bounded
        # (two thumbnail processes plus one audio process) and avoids splits.
        from concurrent.futures import ThreadPoolExecutor
        import threading
        print(f"[Launcher] Preparing {thumb_count} timeline thumbnails with 2 workers + waveform worker")
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="capcap-thumbs") as thumbnail_pool:
            # Keep waveform CPU/audio work independent from the two thumbnail
            # slots so all three tasks can progress concurrently.
            waveform_result = []
            waveform_error = []
            def run_waveform():
                try:
                    waveform_result.extend(build_waveform())
                except Exception as exc:
                    waveform_error.append(exc)
            waveform_thread = threading.Thread(target=run_waveform, name="capcap-waveform", daemon=True)
            waveform_thread.start()
            thumbnails = [item for item in thumbnail_pool.map(build_thumbnail, enumerate(timestamps)) if item]
            waveform_thread.join()
        if waveform_error:
            raise waveform_error[0]
        waveform, duration_s = waveform_result if waveform_result else ([], duration_s)

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump({
                "visual_version": 4, "source": source, "size": int(stat.st_size), "mtime_ns": int(stat.st_mtime_ns),
                "duration_s": float(duration_s), "waveform": waveform, "thumbnails": thumbnails,
            }, handle)
        print(f"[Launcher] Timeline visuals prepared: waveform={len(waveform)}, thumbnails={len(thumbnails)}")
    except Exception as exc:
        print(f"[Launcher] Timeline visual preparation skipped: {exc}")


class LauncherWindow(QDialog):
    hardwareProbed = Signal(bool, str, bool)

    def __init__(self):
        super().__init__()
        self.selected_video = ""
        preferred = str(os.getenv("CAPCAP_DEVICE", "") or "").strip().lower()
        self.selected_device = preferred if preferred in {"cpu", "cuda"} else "cpu"
        self._device_preference_explicit = preferred in {"cpu", "cuda"}
        self._hardware_state = (False, "", False)
        self._thumbnail_dir = os.path.join(workspace_root(), "temp", "launcher_thumbs")

        from runtime_paths import asset_path
        from PySide6.QtGui import QIcon
        logo = asset_path("capcap.png")
        if os.path.exists(logo):
            self.setWindowIcon(QIcon(logo))

        self.setWindowTitle("CapCap — Dịch video & lồng tiếng")
        self.setMinimumSize(1040, 680)
        self.resize(1360, 820)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #08111f;
                color: #d7e7f7;
                font-family: "Segoe UI";
                font-size: 12px;
            }
            QLabel#eyebrow { color:#4ed0b3; font-size:10px; font-weight:800; }
            QLabel#pageTitle { color:#ffffff; font-size:24px; font-weight:800; }
            QLabel#sectionTitle { color:#ffffff; font-size:18px; font-weight:800; }
            QLabel#muted { color:#9bb2ca; }
            QLabel#cardLabel { color:#8ad7ff; font-size:10px; font-weight:700; }
            QLabel#cardValue { color:#ffffff; font-size:14px; font-weight:800; }
            #readinessCard {
                background-color:#121b2b; border:1px solid #263850; border-radius:10px;
            }
            QPushButton {
                background:#1b2b42; color:#dcebfa; border:1px solid #36516e;
                border-radius:8px; padding:8px 13px; font-weight:700;
            }
            QPushButton:hover, QPushButton:focus { border:2px solid #4ed0b3; }
            QPushButton#primaryButton { background:#4ed0b3; color:#06141b; border:0; }
            QPushButton#primaryButton:hover { background:#72e0c8; }
            QPushButton#dangerButton { background:#3a2630; color:#ffb7c0; border-color:#70404e; }
            QScrollArea { background:transparent; border:0; }
        """)

        self.hardwareProbed.connect(self._apply_hardware_probe)
        self._build_ui()
        QTimer.singleShot(0, self._load_recent)
        QTimer.singleShot(0, self._validate_resources_for_device)
        QTimer.singleShot(0, self._start_hardware_probe)

    def _build_legacy_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("CapCap V7")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #ffffff;")
        subtitle = QLabel("Video Translation & Voiceover Studio")
        subtitle.setStyleSheet("font-size: 12px; color: #6ee7d6;")


        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        has_gpu, gpu_name, cuda_ready = self._detect_gpu_with_cuda()
        gpu_usable = has_gpu and cuda_ready
        self.selected_device = "cuda" if gpu_usable else "cpu"
        LauncherWindow._gpu_name = gpu_name if has_gpu else ""

        self._gpu_label = QLabel()
        header_text.addWidget(self._gpu_label)
        self._update_gpu_label(has_gpu, gpu_name, cuda_ready)

        self._missing_label = QLabel("", self)
        self._missing_label.setWordWrap(True)
        self._missing_label.setStyleSheet(
            "font-size: 11px; color: #ff6b6b; padding: 4px 8px;"
            " background-color: #3b1a1a; border: 1px solid #ff6b6b55; border-radius: 6px;"
        )
        self._missing_label.hide()
        header_text.addWidget(self._missing_label)

        device_row = QHBoxLayout()
        device_row.setSpacing(0)
        self.cpu_btn = QPushButton("CPU")
        self.cpu_btn.setCheckable(True)
        self.cpu_btn.setChecked(not gpu_usable)
        self.cpu_btn.setEnabled(True)
        self.gpu_btn = QPushButton("GPU (Recommended)" if gpu_usable else "GPU (N/A)")
        self.gpu_btn.setCheckable(True)
        self.gpu_btn.setChecked(gpu_usable)
        self.gpu_btn.setEnabled(gpu_usable)

        btn_style = """
            QPushButton {
                color: #8ea3bb; border: 1px solid #2f4868; padding: 3px 10px;
                font-size: 11px; font-weight: 600; border-radius: 0;
                background-color: transparent;
            }
            QPushButton:checked {
                background-color: #1a3a5c; color: #8ad7ff; border-color: #4ecdc4;
            }
            QPushButton:disabled {
                color: #445566; border-color: #1e3045;
            }
        """
        self.cpu_btn.setStyleSheet(btn_style + "QPushButton { border-top-left-radius: 6px; border-bottom-left-radius: 6px; }")
        self.gpu_btn.setStyleSheet(btn_style + "QPushButton { border-top-right-radius: 6px; border-bottom-right-radius: 6px; }")

        def _select_cpu(checked):
            if checked:
                self.gpu_btn.setChecked(False)
                self._set_selected_device("cpu")
                self._validate_resources_for_device()
            elif not self.gpu_btn.isChecked():
                self.cpu_btn.setChecked(True)

        def _select_gpu(checked):
            if checked:
                self.cpu_btn.setChecked(False)
                self._set_selected_device("cuda")
                self._validate_resources_for_device()
            elif not self.cpu_btn.isChecked():
                self.gpu_btn.setChecked(True)

        self.cpu_btn.clicked.connect(_select_cpu)
        self.gpu_btn.clicked.connect(_select_gpu)

        device_row.addWidget(self.cpu_btn)
        device_row.addWidget(self.gpu_btn)
        device_row.addStretch()
        header_text.addLayout(device_row)
        header.addLayout(header_text, 1)

        action_rows = QVBoxLayout()
        action_rows.setSpacing(6)
        action_row_one = QHBoxLayout()
        action_row_one.setSpacing(6)
        action_row_two = QHBoxLayout()
        action_row_two.setSpacing(6)

        self.new_btn = QPushButton("+ New Project")
        self.new_btn.setMinimumHeight(44)
        self.new_btn.setMinimumWidth(150)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ecdc4;
                color: #0a101e;
                font-weight: 700;
                font-size: 14px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #6ee7d6;
            }
        """)
        self.new_btn.clicked.connect(self._on_new_project)
        action_row_one.addWidget(self.new_btn)

        self.split_btn = QPushButton("Split Video")
        self.split_btn.setMinimumHeight(44)
        self.split_btn.setMinimumWidth(120)
        self.split_btn.setStyleSheet("""
            QPushButton {
                background-color: #22344d;
                color: #8ad7ff;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid #34506f;
            }
            QPushButton:hover {
                background-color: #29405d;
            }
        """)
        self.split_btn.clicked.connect(self._on_split_video)
        action_row_one.addWidget(self.split_btn)

        self.resource_btn = QPushButton("Manage Resources")
        self.resource_btn.setMinimumHeight(44)
        self.resource_btn.setMinimumWidth(150)
        self.resource_btn.setStyleSheet("""
            QPushButton {
                background-color: #22344d;
                color: #8ad7ff;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid #34506f;
            }
            QPushButton:hover {
                background-color: #29405d;
            }
        """)
        self.resource_btn.clicked.connect(self._on_manage_resources)
        action_row_one.addWidget(self.resource_btn)

        self.clean_video_btn = QPushButton("Clean Video Data")
        self.clean_video_btn.setMinimumHeight(44)
        self.clean_video_btn.setMinimumWidth(145)
        self.clean_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a2630;
                color: #ffb3bd;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid #70404e;
            }
            QPushButton:hover { background-color: #52303c; }
        """)
        self.clean_video_btn.setToolTip("Remove generated project data and video preview caches")
        self.clean_video_btn.clicked.connect(self._on_clean_video_data)
        action_row_two.addWidget(self.clean_video_btn)

        self.open_project_btn = QPushButton("Open Project Folder")
        self.open_project_btn.setMinimumHeight(44)
        self.open_project_btn.setMinimumWidth(165)
        self.open_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #22344d;
                color: #8ad7ff;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid #34506f;
            }
            QPushButton:hover { background-color: #29405d; }
        """)
        self.open_project_btn.setToolTip("Open the CapCap projects folder")
        self.open_project_btn.clicked.connect(self._on_open_project_folder)
        action_row_two.insertWidget(0, self.open_project_btn)

        self.about_btn = QPushButton("About / Help")
        self.about_btn.setMinimumHeight(44)
        self.about_btn.setMinimumWidth(145)
        self.about_btn.setStyleSheet("""
            QPushButton {
                background-color: #22344d;
                color: #8ad7ff;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid #34506f;
            }
            QPushButton:hover { background-color: #29405d; }
        """)
        self.about_btn.clicked.connect(self._on_about)
        action_row_two.addWidget(self.about_btn)
        action_row_two.addStretch()

        action_rows.addLayout(action_row_one)
        action_rows.addLayout(action_row_two)
        header.addLayout(action_rows)
        root.addLayout(header)

        self.section_label = QLabel("Recent Projects")
        self.section_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #8ad7ff;")
        root.addWidget(self.section_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.grid_widget)
        root.addWidget(scroll, 1)

        self.empty_label = QLabel("No recent projects. Click \"+ New Project\" to start.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #556677; font-size: 13px;")
        self.empty_label.hide()
        root.addWidget(self.empty_label)

        self.loading_label = QLabel("Preparing video...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #4ecdc4; font-size: 16px; font-weight: 700; padding: 20px;")
        self.loading_label.hide()
        root.addWidget(self.loading_label)

    def _make_readiness_card(self, label: str, value: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
        card = QFrame(self)
        card.setObjectName("readinessCard")
        card.setMinimumHeight(145)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("cardLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("cardValue")
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return card, layout, value_widget

    @staticmethod
    def _pill(text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"color:{color}; background:#142437; border:1px solid {color}; "
            "border-radius:9px; padding:3px 8px; font-size:10px; font-weight:700;"
        )
        return label

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(16)

        topbar = QHBoxLayout()
        mark = QLabel("C")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(28, 28)
        mark.setStyleSheet("background:#72d7ea;color:#07131d;border-radius:8px;font-size:14px;font-weight:900;")
        brand = QLabel("CapCap V7")
        brand.setStyleSheet("color:#ffffff;font-size:15px;font-weight:900;")
        product = QLabel("│  Video Translation & Voiceover Studio")
        product.setStyleSheet("color:#b9cee4;font-size:11px;font-weight:600;")
        topbar.addWidget(mark)
        topbar.addWidget(brand)
        topbar.addWidget(product)
        topbar.addStretch()
        self.resource_btn = QPushButton("Tài nguyên & cài đặt")
        self.resource_btn.setAccessibleName("Mở tài nguyên và cài đặt")
        self.resource_btn.clicked.connect(self._on_manage_resources)
        topbar.addWidget(self.resource_btn)
        root.addLayout(topbar)

        heading = QHBoxLayout()
        heading_text = QVBoxLayout()
        eyebrow = QLabel("BẮT ĐẦU")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Sẵn sàng trước khi chạy")
        title.setObjectName("pageTitle")
        description = QLabel("Chọn thiết bị, xác minh model bắt buộc rồi mở hoặc tạo dự án.")
        description.setObjectName("muted")
        heading_text.addWidget(eyebrow)
        heading_text.addWidget(title)
        heading_text.addWidget(description)
        heading.addLayout(heading_text, 1)
        self.open_project_btn = QPushButton("Mở thư mục dự án")
        self.open_project_btn.setAccessibleName("Mở thư mục dự án CapCap")
        self.open_project_btn.clicked.connect(self._on_open_project_folder)
        heading.addWidget(self.open_project_btn, 0, Qt.AlignBottom)
        self.new_btn = QPushButton("＋ Dự án mới")
        self.new_btn.setObjectName("primaryButton")
        self.new_btn.setMinimumHeight(42)
        self.new_btn.setAccessibleName("Tạo dự án mới từ video")
        self.new_btn.clicked.connect(self._on_new_project)
        heading.addWidget(self.new_btn, 0, Qt.AlignBottom)
        root.addLayout(heading)

        readiness = QHBoxLayout()
        readiness.setSpacing(12)

        device_card, device_layout, self._device_value = self._make_readiness_card(
            "Thiết bị xử lý", "Đang kiểm tra phần cứng…"
        )
        self._gpu_label = QLabel("Đang xác minh CUDA và VRAM")
        self._gpu_label.setObjectName("muted")
        self._gpu_label.setWordWrap(True)
        device_layout.addWidget(self._gpu_label)
        device_row = QHBoxLayout()
        device_row.setSpacing(0)
        self.cpu_btn = QPushButton("CPU")
        self.cpu_btn.setCheckable(True)
        self.gpu_btn = QPushButton("GPU · Khuyến nghị")
        self.gpu_btn.setCheckable(True)
        self.cpu_btn.setChecked(self.selected_device == "cpu")
        self.gpu_btn.setChecked(self.selected_device == "cuda")
        device_style = (
            "QPushButton{border-radius:0;background:#101b2b;color:#9bb2ca;}"
            "QPushButton:checked{background:#1b4361;color:#8ad7ff;border-color:#4ed0b3;}"
            "QPushButton:disabled{color:#56677a;border-color:#25364a;}"
        )
        self.cpu_btn.setStyleSheet(device_style)
        self.gpu_btn.setStyleSheet(device_style)
        self.cpu_btn.clicked.connect(lambda checked: self._choose_device("cpu", checked))
        self.gpu_btn.clicked.connect(lambda checked: self._choose_device("cuda", checked))
        device_row.addWidget(self.cpu_btn, 1)
        device_row.addWidget(self.gpu_btn, 1)
        device_layout.addLayout(device_row)
        readiness.addWidget(device_card, 1)

        profile_card, profile_layout, _profile_value = self._make_readiness_card(
            "Hồ sơ thực thi", "Hybrid · mặc định"
        )
        profile_header = QHBoxLayout()
        profile_header.addStretch()
        profile_header.addWidget(self._pill("● Chỉ gửi văn bản", "#8ad7ff"))
        profile_layout.insertLayout(1, profile_header)
        profile_description = QLabel(
            "Media, ASR, TTS và xuất chạy local; dịch văn bản dùng provider đã chọn."
        )
        profile_description.setObjectName("muted")
        profile_description.setWordWrap(True)
        profile_layout.addWidget(profile_description)
        profile_button = QPushButton("Xem cấu hình")
        profile_button.clicked.connect(self._on_manage_resources)
        profile_layout.addWidget(profile_button, 0, Qt.AlignLeft)
        readiness.addWidget(profile_card, 1)

        resource_card, resource_layout, self._resource_value = self._make_readiness_card(
            "Kiểm tra bắt buộc", "Đang kiểm tra…"
        )
        resource_header = QHBoxLayout()
        resource_header.addStretch()
        self._resource_badge = self._pill("● Đang kiểm tra", "#8ad7ff")
        resource_header.addWidget(self._resource_badge)
        resource_layout.insertLayout(1, resource_header)
        self._missing_label = QLabel("Đang xác minh model và runtime cho thiết bị đã chọn.")
        self._missing_label.setObjectName("muted")
        self._missing_label.setWordWrap(True)
        resource_layout.addWidget(self._missing_label)
        resource_manage = QPushButton("Quản lý tài nguyên")
        resource_manage.clicked.connect(self._on_manage_resources)
        resource_layout.addWidget(resource_manage, 0, Qt.AlignLeft)
        readiness.addWidget(resource_card, 1)
        root.addLayout(readiness)

        recent_heading = QHBoxLayout()
        recent_text = QVBoxLayout()
        self.section_label = QLabel("Dự án gần đây")
        self.section_label.setObjectName("sectionTitle")
        recent_hint = QLabel("Tiếp tục đúng bước đã dừng; không chạy lại toàn bộ pipeline.")
        recent_hint.setObjectName("muted")
        recent_text.addWidget(self.section_label)
        recent_text.addWidget(recent_hint)
        recent_heading.addLayout(recent_text, 1)
        self.clean_video_btn = QPushButton("Dọn dữ liệu video…")
        self.clean_video_btn.setObjectName("dangerButton")
        self.clean_video_btn.setToolTip("Xóa project sinh ra và cache xem trước; không xóa video nguồn/model")
        self.clean_video_btn.clicked.connect(self._on_clean_video_data)
        recent_heading.addWidget(self.clean_video_btn, 0, Qt.AlignBottom)
        root.addLayout(recent_heading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:#08111f;border:0;}"
            "QScrollArea > QWidget > QWidget{background:#08111f;}"
        )
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background:#08111f;")
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.grid_widget)
        root.addWidget(scroll, 1)

        self.empty_label = QLabel("")
        self.empty_label.hide()
        self.loading_label = QLabel("Đang chuẩn bị video…")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color:#4ed0b3;font-size:14px;font-weight:700;padding:12px;")
        self.loading_label.hide()
        root.addWidget(self.loading_label)

        # Kept as non-primary compatibility actions; the approved Launcher
        # reserves its visible hierarchy for create/open/readiness/resume.
        self.split_btn = QPushButton("Chia video")
        self.split_btn.clicked.connect(self._on_split_video)
        self.split_btn.hide()
        self.about_btn = QPushButton("Trợ giúp")
        self.about_btn.clicked.connect(self._on_about)
        self.about_btn.hide()

    def _choose_device(self, device: str, checked: bool) -> None:
        if not checked:
            active = self.gpu_btn if device == "cpu" else self.cpu_btn
            if not active.isChecked():
                (self.cpu_btn if device == "cpu" else self.gpu_btn).setChecked(True)
            return
        self._device_preference_explicit = True
        self.cpu_btn.setChecked(device == "cpu")
        self.gpu_btn.setChecked(device == "cuda")
        self._set_selected_device(device)
        self._validate_resources_for_device()

    def _start_hardware_probe(self) -> None:
        def probe() -> None:
            has_gpu, gpu_name, cuda_ready = self._detect_gpu_with_cuda()
            self.hardwareProbed.emit(has_gpu, gpu_name, cuda_ready)

        threading.Thread(target=probe, name="capcap-launcher-probe", daemon=True).start()

    def _apply_hardware_probe(self, has_gpu: bool, gpu_name: str, cuda_ready: bool) -> None:
        self._hardware_state = (has_gpu, gpu_name, cuda_ready)
        LauncherWindow._gpu_name = gpu_name if has_gpu else ""
        if has_gpu and cuda_ready and not self._device_preference_explicit:
            self.selected_device = "cuda"
            self.cpu_btn.setChecked(False)
            self.gpu_btn.setChecked(True)
        elif self.selected_device == "cuda" and not (has_gpu and cuda_ready):
            self.selected_device = "cpu"
            self.cpu_btn.setChecked(True)
            self.gpu_btn.setChecked(False)
        self.gpu_btn.setEnabled(has_gpu and cuda_ready)
        self.gpu_btn.setText("GPU · Khuyến nghị" if has_gpu and cuda_ready else "GPU · Chưa sẵn sàng")
        self._update_gpu_label(has_gpu, gpu_name, cuda_ready)
        self._validate_resources_for_device()

    def accept(self):
        if not self.selected_video or not os.path.exists(self.selected_video):
            super().accept()
            return

        try:
            service = self._resource_service()
            is_ok, missing, _advisory = self._launch_resource_state(service)
            if not is_ok:
                from PySide6.QtWidgets import QMessageBox
                labels = [label for _rid, label in missing]
                if self.selected_device == "cpu":
                    prefix = "CPU mode needs:"
                else:
                    prefix = "GPU mode needs:"
                mb = QMessageBox(self)
                mb.setIcon(QMessageBox.Warning)
                mb.setWindowTitle("Missing Resources")
                mb.setText(f"{prefix}\n\n" + "\n".join(f"- {label}" for label in labels))
                mb.setInformativeText("Open Manage Resources to download them.")
                mb.addButton("Manage Resources", QMessageBox.AcceptRole)
                mb.addButton("Close", QMessageBox.RejectRole)
                mb.setStyleSheet(MSG_STYLE)
                mb.exec()
                self._validate_resources_for_device()
                return
        except Exception as exc:
            print(f"[Launcher] Resource validation failed: {exc}")

        duration = _get_video_duration(self.selected_video)
        MAX_DURATION = 7200
        if duration > MAX_DURATION:
            h = int(duration // 3600)
            m = int((duration % 3600) // 60)
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self, "Video Too Long",
                f"This video is {h}h {m}m long.\nCapCap works best with videos under 2 hours.\n\n"
                "Use 'Split Video' to cut it into 2-hour segments first.",
                QMessageBox.Ok,
            )
            reply.setStyleSheet(MSG_STYLE)
            return

        self._set_selected_device(self.selected_device)
        self.loading_label.show()
        self.loading_label.setText("Preparing thumbnails and waveform...\nLarge videos may continue preparing in the editor.")
        self.new_btn.setEnabled(False)
        self._extraction_done = False
        self._preprocess_started_at = time.monotonic()
        self._preprocess_continued_in_background = False
        import threading
        def _preprocess():
            from runtime_paths import workspace_root
            temp_root = os.path.join(workspace_root(), "temp")
            _prepare_timeline_visual_cache(self.selected_video, temp_root)
            self._extraction_done = True
        threading.Thread(target=_preprocess, daemon=True).start()
        self._loader_timer = QTimer()
        self._loader_timer.timeout.connect(self._on_loader_tick)
        self._loader_timer.start(200)

    def _on_loader_tick(self):
        if not getattr(self, "_extraction_done", False):
            # Do not hold the launcher hostage while a long video is being
            # sampled.  The cache worker is filesystem-only and can safely
            # finish after the editor opens; the editor has its own cache
            # consumers/fallback workers for any assets not ready yet.
            started = float(getattr(self, "_preprocess_started_at", 0.0) or 0.0)
            if started and time.monotonic() - started >= 12.0:
                self._preprocess_continued_in_background = True
                print("[Launcher] Timeline visual cache is still preparing; continuing in background.")
                self._loader_timer.stop()
                self._finish_accept()
            return
        self._loader_timer.stop()
        self._finish_accept()

    def _finish_accept(self):
        self.loading_label.hide()
        self.new_btn.setEnabled(True)
        self._save_device_env()
        super().accept()

    @staticmethod
    def _save_device_env():
        device = getattr(LauncherWindow, "_selected_device", "cuda")
        gpu_name = getattr(LauncherWindow, "_gpu_name", "")
        print(f"[Launcher] Saving CAPCAP_DEVICE={device}, GPU={gpu_name}")
        os.environ["CAPCAP_DEVICE"] = device
        os.environ["CAPCAP_GPU_NAME"] = gpu_name
        # ``__file__`` points inside _internal in a PyInstaller build. The
        # writable package root is the only place both later GUI launches and
        # the spawned worker can consistently read.
        env_path = os.path.join(workspace_root(), ".env")
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith("CAPCAP_DEVICE="):
                    lines[i] = f"CAPCAP_DEVICE={device}\n"
                    found = True
                    break
            if not found:
                lines.append(f"CAPCAP_DEVICE={device}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"[Launcher] Failed to write .env: {e}")

    def _set_selected_device(self, device: str) -> None:
        """Apply the launcher choice immediately and make it authoritative."""
        normalized = "cuda" if str(device or "").strip().lower() == "cuda" else "cpu"
        self.selected_device = normalized
        LauncherWindow._selected_device = normalized
        # The Main UI and its local worker inherit this exact value. Do not
        # wait for thumbnail preprocessing to finish before publishing it.
        os.environ["CAPCAP_DEVICE"] = normalized

    def _resource_service(self):
        from runtime_paths import workspace_root
        from services import ResourceDownloadService
        return ResourceDownloadService(workspace_root())

    def _launch_resource_state(self, service):
        """Return launch-blocking and advisory resource requirements.

        SenseVoice has a recovery download for installations where the
        bundled model cannot be detected, but its absence must not prevent a
        user from opening the Main UI.  The Generate/prepare workflow still
        performs the exact runtime validation before transcription starts.
        GPU requirements such as the CUDA pack remain launch-blocking.
        """
        _validated, missing = service.validate_device(self.selected_device)
        blocking = []
        advisory = []
        for resource_id, label in missing:
            if str(resource_id or "").strip().lower().startswith("sensevoice:"):
                advisory.append((resource_id, label))
            else:
                blocking.append((resource_id, label))
        return (not blocking), blocking, advisory

    def _validate_resources_for_device(self):
        try:
            service = self._resource_service()
        except Exception as exc:
            print(f"[Launcher] Failed to load resource service: {exc}")
            self.new_btn.setEnabled(True)
            return
        device = self.selected_device
        is_ok, missing, advisory = self._launch_resource_state(service)
        self.new_btn.setEnabled(is_ok)
        requirements = list(service.get_device_requirements(device))
        missing_ids = {resource_id for resource_id, _label in [*missing, *advisory]}
        ready_count = sum(1 for resource_id, _label in requirements if resource_id not in missing_ids)
        self._resource_value.setText(f"{ready_count}/{len(requirements)} tài nguyên")
        if is_ok and not advisory:
            self._resource_badge.setText("● Sẵn sàng")
            self._resource_badge.setStyleSheet(
                "color:#54d18b;background:#142437;border:1px solid #54d18b;"
                "border-radius:9px;padding:3px 8px;font-size:10px;font-weight:700;"
            )
            self._missing_label.setText("Các tài nguyên bắt buộc cho thiết bị đã chọn đã sẵn sàng.")
            if hasattr(self, "new_btn") and self.new_btn.toolTip():
                self.new_btn.setToolTip("")
        elif is_ok:
            labels = [label for _rid, label in advisory]
            text = (
                f"Có thể mở dự án. Tùy chọn cần bổ sung: {', '.join(labels)}; "
                "cài trong Quản lý tài nguyên trước khi dùng tính năng tương ứng."
            )
            self._resource_badge.setText(f"● {len(advisory)} cần xử lý")
            self._resource_badge.setStyleSheet(
                "color:#ffd400;background:#2c260e;border:1px solid #8b6d00;"
                "border-radius:9px;padding:3px 8px;font-size:10px;font-weight:700;"
            )
            self._missing_label.setText(text)
            self.new_btn.setToolTip(text)
        else:
            labels = [label for _rid, label in missing]
            if advisory:
                labels.extend(label for _rid, label in advisory)
            mode = "CPU" if device == "cpu" else "GPU"
            text = f"{mode} chưa thể chạy: thiếu {', '.join(labels)}. Mở Quản lý tài nguyên để cài."
            self._resource_badge.setText(f"● {len(missing)} chặn chạy")
            self._resource_badge.setStyleSheet(
                "color:#ff6b6b;background:#321b24;border:1px solid #8f3d50;"
                "border-radius:9px;padding:3px 8px;font-size:10px;font-weight:700;"
            )
            self._missing_label.setText(text)
            self.new_btn.setToolTip(text)
        try:
            for i in range(self.grid.count()):
                item = self.grid.itemAt(i)
                if item is None:
                    continue
                widget = item.widget()
                if isinstance(widget, ProjectCard):
                    widget.setEnabled(is_ok)
        except Exception:
            pass

    def _load_recent(self):
        projects = _load_recent_projects()
        os.makedirs(self._thumbnail_dir, exist_ok=True)

        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        existing = [p for p in projects if os.path.exists(p.get("video_path", ""))]
        if existing != projects:
            _save_recent_projects(None, existing)

        self.empty_label.hide()

        columns = min(3, max(1, (self.grid_widget.width() - 24) // 300))
        for i, proj in enumerate(existing):
            card = ProjectCard(proj["video_path"], self._thumbnail_dir, self)
            row, col = divmod(i, max(1, columns))
            self.grid.addWidget(card, row, col)
            self.grid.setColumnStretch(col, 1)
        drop_index = len(existing)
        row, col = divmod(drop_index, max(1, columns))
        self.grid.addWidget(DropProjectCard(self, self), row, col)
        self.grid.setColumnStretch(col, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._load_recent)

    def dragEnterEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()] if event.mimeData().hasUrls() else []
        if any(is_supported_video_path(path) for path in paths):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()] if event.mimeData().hasUrls() else []
        selected = next((path for path in paths if is_supported_video_path(path)), "")
        if not selected:
            event.ignore()
            return
        self.selected_video = os.path.normpath(selected)
        event.acceptProposedAction()
        self.accept()

    def _on_new_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video nguồn", "",
            "Video (*.mp4 *.mkv *.avi *.mov *.webm);;Tất cả tệp (*)"
        )
        if is_supported_video_path(path):
            self.selected_video = os.path.normpath(path)
            self.accept()

    def _on_manage_resources(self):
        from views.resource_manager import open_resource_manager
        open_resource_manager(parent=self)
        self._validate_resources_for_device()

    def _on_open_project_folder(self):
        from PySide6.QtWidgets import QMessageBox
        projects_dir = os.path.join(workspace_root(), "projects")
        try:
            os.makedirs(projects_dir, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(projects_dir)
            else:
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(projects_dir))
        except Exception as exc:
            message = QMessageBox(QMessageBox.Warning, "Open Project Folder",
                f"Could not open the projects folder:\n\n{exc}", QMessageBox.Ok, self)
            message.setStyleSheet(MSG_STYLE)
            message.exec()

    def _on_clean_video_data(self):
        from PySide6.QtWidgets import QMessageBox

        confirm = QMessageBox(QMessageBox.Warning, "Clean Video Data",
            "Remove all generated project data and video preview caches?\n\n"
            "Source videos, downloaded models, Piper voices, CUDA files, and application resources will not be touched.",
            QMessageBox.Yes | QMessageBox.No, self)
        confirm.setStyleSheet(MSG_STYLE)
        if confirm.exec() != QMessageBox.Yes:
            return

        # Keep generated project/cache data in the explicit writable runtime
        # root rather than deriving it from a module location.
        root = workspace_root()
        targets = [
            os.path.join(root, "projects"),
            os.path.join(root, "temp"),
        ]

        # Project cards can still own loaded thumbnail pixmaps from temp.
        # Detach them and process their deferred deletion before removing the
        # cache tree; this avoids a common first-click Windows file lock.
        try:
            from PySide6.QtWidgets import QApplication
            for index in reversed(range(self.grid.count())):
                item = self.grid.takeAt(index)
                widget = item.widget() if item is not None else None
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            QApplication.processEvents()
        except Exception:
            pass

        removed = 0
        errors = []
        for target in targets:
            if not os.path.exists(target):
                continue
            last_error = None
            # FFmpeg/thumbnail work can release a file just after the user
            # confirms cleanup. Retry briefly instead of making the user
            # click Clean Video Data a second time.
            for attempt in range(5):
                try:
                    shutil.rmtree(target)
                    removed += 1
                    last_error = None
                    break
                except FileNotFoundError:
                    last_error = None
                    break
                except OSError as exc:
                    last_error = exc
                    if attempt < 4:
                        try:
                            QApplication.processEvents()
                        except Exception:
                            pass
                        time.sleep(0.25 * (attempt + 1))
            if last_error is not None:
                errors.append(f"{os.path.basename(target)}: {last_error}")
        for target in targets:
            try:
                os.makedirs(target, exist_ok=True)
            except OSError:
                pass
        # Cleaning all generated project data also resets the launcher history;
        # no deleted project should remain listed in recent_projects.json.
        try:
            _save_recent_projects(None, [])
            self._load_recent()
        except Exception as exc:
            errors.append(f"recent projects: {exc}")

        if errors:
            detail = "\n".join(errors)
            message = QMessageBox(QMessageBox.Warning, "Clean Video Data",
                f"Some data could not be removed:\n\n{detail}", QMessageBox.Ok, self)
            message.setStyleSheet(MSG_STYLE)
            message.exec()
        else:
            message = QMessageBox(QMessageBox.Information, "Clean Video Data",
                "Generated project data and video caches were cleared.", QMessageBox.Ok, self)
            message.setStyleSheet(MSG_STYLE)
            message.exec()

    def _on_about(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices, QPixmap
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("About CapCap")
        dialog.setMinimumSize(650, 650)
        dialog.setStyleSheet("QDialog { background: #0a101e; color: #d7e3f4; }")
        layout = QVBoxLayout(dialog)
        title = QLabel("CapCap V7 — Tool Information", dialog)
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        layout.addWidget(title)

        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet(
            "QTextBrowser { background: #0f1928; color: #d7e3f4; border: 1px solid #1e3045; "
            "border-radius: 8px; padding: 10px; }"
        )
        browser.setHtml("""
        <h3 style='color:#8ad7ff;'>Description</h3>
        <p>CapCap is a Windows application that supports both CPU and GPU processing.</p>
        <p>GPU mode provides the best overall experience and performance. GPU acceleration currently supports NVIDIA GPUs.</p>
        <p>If CUDA is not detected correctly, first update your NVIDIA GPU driver. If needed, install CUDA 12.8 from:<br>
        <a href='https://developer.nvidia.com/cuda-12-8-0-download-archive'>CUDA 12.8 Download Archive</a></p>

        <h3 style='color:#8ad7ff;'>Tutorial / Resource Setup</h3>
        <p>Download the resource, then place it in the matching CapCap folder:</p>
        <table cellspacing='6'>
        <tr><td><b>Whisper models</b></td><td><code>CapCap\\models\\faster_whisper</code></td></tr>
        <tr><td><b>CUDA / cuDNN runtime</b></td><td><code>CapCap\\bin\\cuda12_fw</code></td></tr>
        <tr><td><b>SenseVoice</b></td><td>Bundled by default in <code>CapCap\\models\\sensevoice</code></td></tr>
        <tr><td><b>RapidOCR models</b></td><td>Bundled by default; optional files use <code>CapCap\\rapidocr\\models</code></td></tr>
        <tr><td><b>Piper voices</b></td><td><code>CapCap\\models\\piper</code> (Vietnamese: shared <code>config.json</code>) or <code>CapCap\\models\\piper-en</code> (English)</td></tr>
        <tr><td><b>Speaker Detection</b></td><td><code>CapCap\\models\\pyannote</code></td></tr>
        </table>
        <p>Resource Manager provides download links for supported optional resources. Extract downloaded archives into the folder shown above.</p>

        <h3 style='color:#8ad7ff;'>How to Setup</h3>
        <p>CapCap has two processing modes: <b>CPU Mode</b> and <b>GPU Mode</b>.</p>
        <p><b>CPU Mode:</b> Ready to use immediately without additional downloads. Optional resources add more models, voices, or features.</p>
        <p><b>GPU Mode:</b> Requires the <b>GPU Acceleration Pack</b>. Download and extract it into <code>CapCap\\bin</code>. Whisper Medium is optional but recommended for better GPU transcription quality.</p>
        <p>Other resources are optional enhancements. CapCap works without them unless you select a feature that needs one.</p>

        <h3 style='color:#8ad7ff;'>How to Use</h3>
        <p><b>Left side:</b> Workflow progress, configuration, and options.</p>
        <p><b>Right side — Top:</b> Video Preview and action buttons on the left; the selected Timeline layer's Inspector on the right.</p>
        <p><b>Right side — Bottom:</b> Timeline Editor and timeline editing actions.</p>
        <ol>
        <li>Use the setup guidance above and download any resources you need.</li>
        <li>Open Settings and select the Subtitle Source and AI Translation provider.</li>
        <li>In Language, select the input and output languages.</li>
        <li>Click <b>Generate</b>: choose <b>Full Pipeline</b> to run automatically, or <b>Step-by-Step</b> for individual phase control.</li>
        </ol>

        <h3 style='color:#8ad7ff;'>Developer Information</h3>
        <p>GitHub: <a href='https://github.com/notepower2k1/CapCap'>github.com/notepower2k1/CapCap</a></p>
        """)
        layout.addWidget(browser, 1)

        donation_row = QHBoxLayout()
        donation_row.setSpacing(18)
        donation_label = QLabel("Donate Vietnam\nScan to support development", dialog)
        donation_label.setStyleSheet("color:#d7e3f4; font-weight:600;")
        qr_label = QLabel(dialog)
        qr_label.setAlignment(Qt.AlignCenter)
        qr_path = asset_path("qr.png")
        qr_pixmap = QPixmap(qr_path)
        if not qr_pixmap.isNull():
            qr_label.setPixmap(qr_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            qr_label.setText("QR unavailable")
        donation_row.addWidget(donation_label)
        donation_row.addWidget(qr_label)
        donation_row.addStretch()

        coffee_group = QHBoxLayout()
        coffee_group.setSpacing(5)
        coffee_text = QLabel("International Donation\nClick to Buy Me a Coffee", dialog)
        coffee_text.setStyleSheet("color:#d7e3f4; font-weight:600;")
        coffee_group.addWidget(coffee_text)
        coffee_path = asset_path("buymeacoffee.png")
        coffee_pixmap = QPixmap(coffee_path)
        coffee_image = QLabel(dialog)
        coffee_image.setAlignment(Qt.AlignCenter)
        if not coffee_pixmap.isNull():
            coffee_image.setPixmap(coffee_pixmap.scaled(190, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            coffee_image.setText("Buy Me a Coffee image unavailable")
        coffee_image.setToolTip("Open Buy Me a Coffee")
        coffee_image.setCursor(Qt.PointingHandCursor)
        coffee_image.setAccessibleName("International Donation - Buy Me a Coffee")
        coffee_image.mousePressEvent = lambda _event: QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/hcaht"))
        coffee_group.addWidget(coffee_image)
        donation_row.addLayout(coffee_group)
        layout.addLayout(donation_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _on_split_video(self):
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QInputDialog
        from PySide6.QtCore import QThread, Signal
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Long Video to Split", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*)"
        )
        if not path:
            return

        duration = _get_video_duration(path)
        if duration <= 7200:
            mb = QMessageBox(QMessageBox.Information, "No Split Needed",
                "This video is under 2 hours. You can open it directly with '+ New Project'.",
                QMessageBox.Ok, self)
            mb.setStyleSheet(MSG_STYLE)
            mb.exec()
            return

        h = int(duration // 3600)
        m = int((duration % 3600) // 60)

        seg_minutes, ok = QInputDialog.getInt(
            self, "Segment Duration",
            f"Video is {h}h {m}m.\nSplit into segments of how many minutes?",
            120, 10, 1440, 10,
        )
        if not ok:
            return

        seg_seconds = seg_minutes * 60
        base, ext = os.path.splitext(path)
        out_pattern = f"{base}_part%03d{ext}"

        reply = QMessageBox(QMessageBox.Question, "Confirm Split",
            f"Split into {seg_minutes}-minute segments using stream copy (no re-encode, fast).\n\n"
            f"Output: {out_pattern}\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, self)
        reply.setStyleSheet(MSG_STYLE)
        if reply.exec() != QMessageBox.Yes:
            return

        progress = QProgressDialog("Splitting video...", None, 0, 0, self)
        progress.setWindowTitle("Split Video")
        progress.setModal(True)
        progress.setCancelButton(None)
        progress.show()

        import subprocess
        import threading

        def _do_split():
            try:
                subprocess.run(
                    [_ffmpeg_path(), "-y", "-i", path, "-c", "copy",
                     "-f", "segment", "-segment_time", str(seg_seconds),
                     "-reset_timestamps", "1", out_pattern],
                    capture_output=True, timeout=3600, **subprocess_hidden_kwargs(),
                )
                progress.accept()
            except Exception as e:
                progress.accept()
                print(f"[Split] Error: {e}")

        threading.Thread(target=_do_split, daemon=True).start()
        progress.exec()

        mb = QMessageBox(QMessageBox.Information, "Done",
            f"Video split into {seg_minutes}-minute segments.\nSaved alongside the original file.",
            QMessageBox.Ok, self)
        mb.setStyleSheet(MSG_STYLE)
        mb.exec()

    def _detect_gpu_with_cuda(self):
        has_gpu = False
        gpu_name = ""
        cuda_ready = False
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10,
                **subprocess_hidden_kwargs(),
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_name = result.stdout.strip().split("\n")[0].strip()
                has_gpu = True
        except Exception:
            pass
        if not has_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    name = torch.cuda.get_device_name(0)
                    vram = torch.cuda.get_device_properties(0).total_mem // (1024 ** 3)
                    gpu_name = f"{name} ({vram}GB)"
                    has_gpu = True
            except Exception:
                pass
        if has_gpu:
            try:
                service = self._resource_service()
                cuda_ready = service.is_requirement_met("cuda:whisper")
            except Exception:
                pass
        return has_gpu, gpu_name, cuda_ready

    def _update_gpu_label(self, has_gpu: bool, gpu_name: str, cuda_ready: bool):
        if has_gpu:
            if cuda_ready:
                self._device_value.setText(gpu_name or "NVIDIA GPU")
                self._gpu_label.setText("● CUDA sẵn sàng · phù hợp Faster-Whisper và VieNeu tuần tự")
                self._gpu_label.setStyleSheet("font-size:11px;color:#54d18b;")
            else:
                self._device_value.setText(gpu_name or "NVIDIA GPU")
                self._gpu_label.setText("● Đã thấy GPU · cần gói tăng tốc CUDA")
                self._gpu_label.setStyleSheet("font-size:11px;color:#ffd400;")
        else:
            self._device_value.setText("CPU cục bộ")
            self._gpu_label.setText("● Không phát hiện GPU NVIDIA khả dụng")
            self._gpu_label.setStyleSheet("font-size:11px;color:#9bb2ca;")

    @staticmethod
    def add_recent(settings_or_none, video_path: str):
        video_path = os.path.normpath(video_path)
        projects = _load_recent_projects()
        projects = [p for p in projects if os.path.exists(p.get("video_path", ""))]
        existing = [p for p in projects if os.path.normpath(p.get("video_path", "")) == video_path]
        if existing:
            projects.remove(existing[0])
        projects.insert(0, {
            "video_path": video_path,
            "opened_at": int(time.time()),
        })
        projects = projects[:12]
        _save_recent_projects(None, projects)


def _thumbnail_name(video_path: str) -> str:
    import hashlib
    h = hashlib.md5(video_path.encode()).hexdigest()
    return f"{h}.jpg"


def show_launcher(settings_or_none) -> str:
    """Show launcher, return selected video path or empty string."""
    w = LauncherWindow()
    if w.exec() == QDialog.Accepted:
        return w.selected_video
    return ""
