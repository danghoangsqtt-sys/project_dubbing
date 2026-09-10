"""Collect a privacy-safe CapCap workstation and runtime readiness report."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_PACKAGES = {
    "PySide6": "PySide6",
    "requests": "requests",
    "python-dotenv": "dotenv",
    "pydub": "pydub",
    "python-mpv": "mpv",
}
PIPELINE_PACKAGES = {
    "faster-whisper": "faster_whisper",
    "ctranslate2": "ctranslate2",
    "vieneu": "vieneu",
    "numpy": "numpy",
    "soundfile": "soundfile",
    "onnxruntime-gpu": "onnxruntime",
    "rapidocr": "rapidocr",
    "sherpa-onnx": "sherpa_onnx",
}


def run_command(
    args: Sequence[str | os.PathLike[str]],
    *,
    timeout: int = 20,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a bounded command without a shell and return decoded output."""

    command = [os.fspath(value) for value in args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            shell=False,
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 124 if isinstance(exc, subprocess.TimeoutExpired) else 127, "", str(exc)


def check(check_id: str, status: str, summary: str, **details: Any) -> dict[str, Any]:
    """Create a normalized check record."""

    if status not in {"pass", "warning", "fail"}:
        raise ValueError(f"Unsupported check status: {status}")
    record: dict[str, Any] = {"id": check_id, "status": status, "summary": summary}
    if details:
        record["details"] = details
    return record


def aggregate_status(checks: Iterable[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    """Warnings remain visible but do not fail the Day 1 execution baseline."""

    counts = {"pass": 0, "warning": 0, "fail": 0}
    for item in checks:
        counts[item["status"]] += 1
    return ("fail" if counts["fail"] else "pass"), counts


def display_path(path: Path) -> str:
    """Avoid embedding user-home paths in committed evidence."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return f"<external>/{resolved.name}"


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def windows_cpu_name() -> str:
    if os.name != "nt":
        return platform.processor() or "unknown"

    try:
        import winreg

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return str(value).strip()
    except OSError:
        return platform.processor() or "unknown"


def windows_release_name(build: str) -> str:
    """Windows 11 still reports kernel major 10; build 22000 is the boundary."""

    try:
        return "Windows 11" if int(build) >= 22_000 else "Windows 10"
    except (TypeError, ValueError):
        return f"Windows {platform.release()}"


def windows_os_details() -> dict[str, str]:
    if os.name != "nt":
        return {
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        }
    details = {"name": f"Windows {platform.release()}", "release": "", "version": platform.version()}
    try:
        import winreg

        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            build = str(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
            display_version = str(winreg.QueryValueEx(key, "DisplayVersion")[0])
            edition = str(winreg.QueryValueEx(key, "EditionID")[0])
        details.update(
            {
                "name": windows_release_name(build),
                "release": display_version,
                "version": platform.version(),
                "build": build,
                "edition": edition,
            }
        )
    except OSError:
        pass
    return details


def total_memory_bytes() -> int:
    if os.name != "nt":
        return 0

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    state = MemoryStatus()
    state.dwLength = ctypes.sizeof(MemoryStatus)
    return int(state.ullTotalPhys) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)) else 0


def python_check() -> dict[str, Any]:
    version = platform.python_version()
    is_311 = sys.version_info[:2] == (3, 11)
    in_venv = sys.prefix != sys.base_prefix
    status = "pass" if is_311 and in_venv else "fail"
    return check(
        "python",
        status,
        f"Python {version}; virtualenv={'yes' if in_venv else 'no'}",
        version=version,
        implementation=platform.python_implementation(),
        executable=display_path(Path(sys.executable)),
        virtualenv=in_venv,
        required="3.11.x in repo-local virtualenv",
    )


def package_check() -> dict[str, Any]:
    packages: list[dict[str, Any]] = []
    base_missing: list[str] = []
    pipeline_missing: list[str] = []
    for scope, mapping in (("base", BASE_PACKAGES), ("pipeline", PIPELINE_PACKAGES)):
        for distribution, module in mapping.items():
            installed = importlib.util.find_spec(module) is not None
            try:
                version = importlib.metadata.version(distribution) if installed else None
            except importlib.metadata.PackageNotFoundError:
                version = "present-version-unknown" if installed else None
            packages.append(
                {
                    "distribution": distribution,
                    "module": module,
                    "scope": scope,
                    "installed": installed,
                    "version": version,
                }
            )
            if not installed:
                (base_missing if scope == "base" else pipeline_missing).append(distribution)
    status = "fail" if base_missing else ("warning" if pipeline_missing else "pass")
    summary = "Base GUI packages ready"
    if base_missing:
        summary = "Missing base GUI packages: " + ", ".join(base_missing)
    elif pipeline_missing:
        summary += "; optional/full-pipeline packages missing: " + ", ".join(pipeline_missing)
    return check("python_packages", status, summary, packages=packages)


def gpu_check() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return check("gpu", "fail", "nvidia-smi is unavailable")
    fields = "name,driver_version,memory.total,memory.free,compute_cap,temperature.gpu"
    code, stdout, stderr = run_command(
        [executable, f"--query-gpu={fields}", "--format=csv,noheader,nounits"]
    )
    if code or not stdout:
        return check("gpu", "fail", "nvidia-smi query failed", error=first_line(stderr))
    values = [value.strip() for value in stdout.splitlines()[0].split(",")]
    if len(values) != 6:
        return check("gpu", "fail", "Unexpected nvidia-smi output", output=stdout[:500])
    name, driver, total, free, capability, temperature = values
    _, banner, banner_error = run_command([executable])
    cuda_match = re.search(r"CUDA(?: UMD)? Version:\s*([0-9.]+)", banner or banner_error)
    cuda_driver_api = cuda_match.group(1) if cuda_match else "unknown"
    total_mib = int(float(total))
    status = "pass" if total_mib >= 12_000 else "warning"
    return check(
        "gpu",
        status,
        f"{name}; {total_mib} MiB; driver {driver}",
        name=name,
        driver_version=driver,
        memory_total_mib=total_mib,
        memory_free_mib=int(float(free)),
        compute_capability=capability,
        cuda_driver_api_version=cuda_driver_api,
        temperature_c=int(float(temperature)),
    )


def inference_runtime_check() -> dict[str, Any]:
    probe = (
        "import json, ctranslate2, onnxruntime as ort; "
        "print(json.dumps({'ctranslate2': ctranslate2.__version__, "
        "'ctranslate2_cuda_devices': ctranslate2.get_cuda_device_count(), "
        "'onnxruntime': ort.__version__, 'onnx_providers': ort.get_available_providers()}))"
    )
    code, stdout, stderr = run_command([sys.executable, "-c", probe], timeout=30)
    if code:
        return check("inference_runtime", "warning", "AI runtime probe failed", error=(stderr or stdout)[-1_000:])
    try:
        details = json.loads(stdout)
    except json.JSONDecodeError:
        return check("inference_runtime", "warning", "AI runtime returned invalid diagnostics", output=stdout[:500])
    ctranslate_cuda = int(details.get("ctranslate2_cuda_devices") or 0)
    onnx_providers = list(details.get("onnx_providers") or [])
    ctranslate_ready = ctranslate_cuda >= 1
    onnx_cuda_ready = "CUDAExecutionProvider" in onnx_providers
    status = "pass" if ctranslate_ready and onnx_cuda_ready else "warning"
    summary = (
        "CTranslate2 and ONNX Runtime expose CUDA"
        if status == "pass"
        else f"CTranslate2 CUDA devices={ctranslate_cuda}; ONNX CUDA provider={'yes' if onnx_cuda_ready else 'no'}"
    )
    return check(
        "inference_runtime",
        status,
        summary,
        **details,
        ctranslate2_cuda_ready=ctranslate_ready,
        onnx_cuda_ready=onnx_cuda_ready,
    )


def media_runtime_check() -> dict[str, Any]:
    ffmpeg = REPO_ROOT / "bin" / "ffmpeg" / "ffmpeg.exe"
    ffprobe = REPO_ROOT / "bin" / "ffmpeg" / "ffprobe.exe"
    missing = [display_path(path) for path in (ffmpeg, ffprobe) if not path.is_file()]
    if missing:
        return check("media_runtime", "fail", "Bundled media runtime is incomplete", missing=missing)
    ffmpeg_code, ffmpeg_out, ffmpeg_err = run_command([ffmpeg, "-hide_banner", "-version"])
    ffprobe_code, ffprobe_out, ffprobe_err = run_command([ffprobe, "-hide_banner", "-version"])
    encoder_code, encoder_out, encoder_err = run_command([ffmpeg, "-hide_banner", "-encoders"])
    encoders = {name: name in encoder_out for name in ("h264_nvenc", "libx264")}
    ok = not (ffmpeg_code or ffprobe_code or encoder_code) and all(encoders.values())
    return check(
        "media_runtime",
        "pass" if ok else "fail",
        "Bundled FFmpeg/ffprobe and H.264 encoders ready" if ok else "Bundled media runtime check failed",
        ffmpeg=display_path(ffmpeg),
        ffmpeg_version=first_line(ffmpeg_out or ffmpeg_err),
        ffprobe=display_path(ffprobe),
        ffprobe_version=first_line(ffprobe_out or ffprobe_err),
        encoders=encoders,
        error=first_line(encoder_err) if encoder_code else "",
    )


def file_inventory(path: Path, patterns: Sequence[str]) -> dict[str, Any]:
    matches: list[Path] = []
    if path.is_dir():
        for pattern in patterns:
            matches.extend(item for item in path.rglob(pattern) if item.is_file())
    unique = sorted(set(matches))
    return {
        "path": display_path(path),
        "exists": path.exists(),
        "matching_files": len(unique),
        "bytes": sum(item.stat().st_size for item in unique),
    }


def resource_check() -> dict[str, Any]:
    resources = [
        ("cuda_runtime", REPO_ROOT / "bin" / "cuda12_fw", ("*.dll",)),
        ("faster_whisper_models", REPO_ROOT / "models" / "faster_whisper", ("model.bin",)),
        ("vieneu_models", REPO_ROOT / "models" / "vieneu", ("*.onnx", "*.safetensors")),
        ("sensevoice", REPO_ROOT / "models" / "sensevoice", ("*.onnx", "tokens.txt")),
        ("piper_voices", REPO_ROOT / "models" / "piper", ("*.onnx",)),
        ("diarization", REPO_ROOT / "models" / "pyannote", ("*.onnx",)),
        ("libmpv", REPO_ROOT / "bin" / "mpv", ("mpv-2.dll", "libmpv-2.dll")),
        ("voice_samples", REPO_ROOT / "assets" / "voices", ("*.wav", "*.mp3", "*.flac")),
    ]
    inventory: list[dict[str, Any]] = []
    missing: list[str] = []
    for resource_id, path, patterns in resources:
        item = {"id": resource_id, **file_inventory(path, patterns)}
        item["status"] = "ready" if item["matching_files"] > 0 and item["bytes"] > 0 else "missing"
        if item["status"] == "missing":
            missing.append(resource_id)
        inventory.append(item)
    summary = "Resource inventory recorded"
    if missing:
        summary += "; install before relevant stages: " + ", ".join(missing)
    return check("resources", "warning" if missing else "pass", summary, resources=inventory)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def video_check(video: Path | None) -> dict[str, Any]:
    if video is None:
        return check("video_probe", "warning", "No local smoke video supplied")
    resolved = video.resolve()
    if not resolved.is_file():
        return check("video_probe", "fail", "Smoke video does not exist", path=display_path(resolved))
    ffprobe = REPO_ROOT / "bin" / "ffmpeg" / "ffprobe.exe"
    code, stdout, stderr = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            resolved,
        ],
        timeout=30,
    )
    try:
        payload = json.loads(stdout) if code == 0 else {}
    except json.JSONDecodeError:
        payload = {}
    streams = payload.get("streams", []) if isinstance(payload, dict) else []
    video_count = sum(item.get("codec_type") == "video" for item in streams)
    audio_count = sum(item.get("codec_type") == "audio" for item in streams)
    duration = float((payload.get("format") or {}).get("duration") or 0)
    valid = code == 0 and video_count >= 1 and audio_count >= 1 and duration > 0
    return check(
        "video_probe",
        "pass" if valid else "fail",
        f"Local video opened: {duration:.3f}s, {video_count} video/{audio_count} audio streams"
        if valid
        else "Local video probe failed",
        path=display_path(resolved),
        size_bytes=resolved.stat().st_size,
        sha256=sha256_file(resolved),
        duration_seconds=round(duration, 3),
        video_streams=video_count,
        audio_streams=audio_count,
        error=first_line(stderr) if code else "",
    )


def gui_smoke_check(video: Path | None) -> dict[str, Any]:
    if video is None or not video.is_file():
        return check("gui_smoke", "fail", "GUI smoke requires an existing --video path")
    smoke_code = r'''
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
video = Path(sys.argv[2]).resolve()
os.chdir(root)
sys.path.insert(0, str(root / "app"))
sys.path.insert(0, str(root / "ui"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from views.launcher import LauncherWindow, ProjectCard, _get_video_duration

app = QApplication([])
window = LauncherWindow()
card = ProjectCard(str(video), str(root / "temp" / "preflight-thumbnails"), window)
window.show()
app.processEvents()
if card.video_path != str(video) or _get_video_duration(str(video)) <= 0:
    raise SystemExit(4)
QTimer.singleShot(200, app.quit)
raise SystemExit(app.exec())
'''
    env = dict(os.environ)
    env.update({"QT_QPA_PLATFORM": "offscreen", "CAPCAP_QUIET": "1"})
    code, stdout, stderr = run_command(
        [sys.executable, "-c", smoke_code, REPO_ROOT, video.resolve()],
        timeout=45,
        env=env,
    )
    message = "PySide6 launcher opened offscreen and accepted the local video"
    if code:
        message = "Offscreen GUI smoke failed"
    diagnostic = (stderr or stdout).strip()
    # Tracebacks are useful at the end, not the first line. Keep a bounded tail
    # so committed evidence stays actionable without becoming a raw runtime log.
    diagnostic = diagnostic[-2_000:]
    return check("gui_smoke", "pass" if code == 0 else "fail", message, exit_code=code, diagnostic=diagnostic)


def build_report(video: Path | None = None, *, gui_smoke: bool = False) -> dict[str, Any]:
    memory_bytes = total_memory_bytes()
    os_details = windows_os_details()
    checks = [
        check(
            "system",
            "pass",
            f"{os_details['name']} {os_details.get('release', '')} on {platform.machine()}".strip(),
            os=os_details,
            architecture=platform.machine(),
            cpu=windows_cpu_name(),
            logical_cpu_count=os.cpu_count(),
            ram_bytes=memory_bytes,
            ram_gib=round(memory_bytes / (1024**3), 2) if memory_bytes else None,
        ),
        python_check(),
        package_check(),
        gpu_check(),
        inference_runtime_check(),
        media_runtime_check(),
        resource_check(),
        video_check(video),
    ]
    if gui_smoke:
        checks.append(gui_smoke_check(video))
    overall, counts = aggregate_status(checks)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "project": "CapCap",
        "task": "1.1",
        "privacy": "No .env values, API credentials, media contents or user-home paths are recorded.",
        "overall_status": overall,
        "counts": counts,
        "checks": checks,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, help="Local video to validate with bundled ffprobe")
    parser.add_argument("--gui-smoke", action="store_true", help="Open launcher/card in Qt offscreen mode")
    parser.add_argument("--json", dest="json_path", type=Path, help="Atomically write the complete report")
    args = parser.parse_args(argv)

    report = build_report(args.video, gui_smoke=args.gui_smoke)
    for item in report["checks"]:
        print(f"[{item['status'].upper():7}] {item['id']}: {item['summary']}")
    print(f"Overall: {report['overall_status'].upper()} ({report['counts']})")
    if args.json_path:
        write_report(args.json_path, report)
        print(f"Report: {display_path(args.json_path)}")
    return 0 if report["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
