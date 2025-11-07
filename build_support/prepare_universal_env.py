"""Utility helpers to prepare a universal macOS runtime before packaging.

This module performs two key tasks:
  1. Ensures `llama_cpp_python` is built with Metal acceleration on Apple Silicon while
     keeping a functional x86_64 slice for Intel Macs.
  2. Optionally stages ffmpeg/ffprobe binaries so audio processing works out of the box.

The functions are written so they can be safely called from build scripts as well as
interactive sessions. All subprocess calls include detailed logging to help diagnose
build failures on CI hosts where toolchains might be missing.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, Optional


LLAMA_CPP_VERSION = "0.3.14"

FFMPEG_RELEASES: Dict[str, Dict[str, str]] = {
    "macos-universal": {
        "url": "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/autobuild-2024-09-28-14-24/ffmpeg-N-118269-g1727b7eb53-macos-universal.tar.xz",
        "sha256": "9a4f6d8a97de7a0c495187b316985cbb46b40df346e1db4dc67e1996f7b9c6dd",
        "archive_root": "ffmpeg-N-118269-g1727b7eb53-macos-universal"
    }
}


def _log(message: str) -> None:
    print(f"[prepare_universal_env] {message}")


def _run(cmd, *, env=None, check=True) -> subprocess.CompletedProcess:
    _log(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, check=check, capture_output=True, text=True)
    if result.stdout:
        _log(result.stdout.strip())
    if result.stderr:
        _log(result.stderr.strip())
    return result


def _llama_cpp_supports_metal() -> bool:
    try:
        result = subprocess.run(
            [
                os.environ.get("PYTHON_EXECUTABLE", os.sys.executable),
                "-c",
                "import json, llama_cpp; print(json.dumps({'metal': bool(getattr(llama_cpp, 'llama_metal_available', lambda: False)()))})",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        _log(f"llama_cpp check failed: {exc.stderr}")
        return False

    try:
        payload = json.loads(result.stdout.strip())
        return bool(payload.get("metal"))
    except json.JSONDecodeError:
        _log(f"Unexpected llama_cpp detection output: {result.stdout}")
        return False


def _ensure_llama_cpp_python() -> bool:
    system = platform.system()
    machine = platform.machine()

    if system != "Darwin":
        _log("Non-macOS host detected; skipping Metal rebuild for llama_cpp_python")
        return True

    if machine != "arm64":
        _log("Intel macOS host detected; keeping CPU-only llama_cpp_python wheel")
        return True

    if _llama_cpp_supports_metal():
        _log("llama_cpp_python already built with Metal support")
        return True

    env = os.environ.copy()
    env.setdefault("CMAKE_ARGS", "-DLLAMA_METAL=on")
    env.setdefault("LLAMA_CPP_METAL", "1")
    env.setdefault("FORCE_CMAKE", "1")
    env.setdefault("ARCHFLAGS", "-arch arm64")

    _log("Rebuilding llama_cpp_python with Metal acceleration enabled")
    try:
        _run(
            [
                os.environ.get("PYTHON_EXECUTABLE", os.sys.executable),
                "-m",
                "pip",
                "install",
                f"llama_cpp_python=={LLAMA_CPP_VERSION}",
                "--force-reinstall",
                "--no-cache-dir",
            ],
            env=env,
        )
    except subprocess.CalledProcessError:
        _log("Failed to rebuild llama_cpp_python with Metal support")
        return False

    return _llama_cpp_supports_metal()


def _download_file(url: str, dest: Path, expected_sha256: Optional[str] = None) -> None:
    import urllib.request

    _log(f"Downloading {url}")
    with urllib.request.urlopen(url) as response, open(dest, "wb") as fh:
        shutil.copyfileobj(response, fh)

    if expected_sha256:
        sha256 = hashlib.sha256()
        with open(dest, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        if digest != expected_sha256:
            raise ValueError(
                f"Checksum mismatch for {url}: expected {expected_sha256}, got {digest}"
            )
        _log(f"Verified SHA256 checksum: {digest}")


def _stage_ffmpeg_binaries() -> bool:
    system = platform.system()
    if system != "Darwin":
        _log("Skipping ffmpeg staging because host is not macOS")
        return True

    release = FFMPEG_RELEASES.get("macos-universal")
    if not release:
        _log("No ffmpeg release metadata available; skipping")
        return False

    bundle_output = Path("resources") / "bin"
    bundle_output.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = bundle_output / "ffmpeg"
    ffprobe_path = bundle_output / "ffprobe"
    if ffmpeg_path.exists() and ffprobe_path.exists():
        _log("ffmpeg binaries already staged")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "ffmpeg.tar.xz"
        try:
            _download_file(release["url"], archive_path, release.get("sha256"))
        except Exception as exc:
            _log(f"Warning: Unable to download ffmpeg bundle ({exc}); continuing without staging ffmpeg")
            return False

        with tarfile.open(archive_path, "r:xz") as tar:
            tar.extractall(tmpdir)

        root = Path(tmpdir) / release["archive_root"]
        candidate_ffmpeg = root / "bin" / "ffmpeg"
        candidate_ffprobe = root / "bin" / "ffprobe"

        if not candidate_ffmpeg.exists() or not candidate_ffprobe.exists():
            _log("Unexpected archive structure; ffmpeg binaries not found")
            return False

        shutil.copy2(candidate_ffmpeg, ffmpeg_path)
        shutil.copy2(candidate_ffprobe, ffprobe_path)
        ffmpeg_path.chmod(0o755)
        ffprobe_path.chmod(0o755)

    _log(f"ffmpeg staged at {ffmpeg_path}")
    return True


def ensure_universal_runtime() -> bool:
    """Prepare environment for universal macOS builds."""

    llama_ok = _ensure_llama_cpp_python()
    ffmpeg_ok = _stage_ffmpeg_binaries()

    if not llama_ok:
        _log("llama_cpp_python Metal rebuild failed")
    if not ffmpeg_ok:
        _log("ffmpeg staging failed")

    # Treat ffmpeg staging as optional; only block on llama rebuild failures.
    return llama_ok


if __name__ == "__main__":
    success = ensure_universal_runtime()
    raise SystemExit(0 if success else 1)

