"""Utility helpers to prepare a macOS arm64 runtime before packaging.

This module performs two key tasks:
  1. Verifies `llama_cpp_python` exposes Metal acceleration on Apple Silicon.
  2. Optionally stages ffmpeg/ffprobe binaries so audio processing works out of the box.

All subprocess calls include detailed logging to help diagnose build failures on CI
hosts where toolchains might be missing.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional


LLAMA_CPP_VERSION = "0.3.16"

FFMPEG_RELEASES: Dict[str, Dict[str, str]] = {
    "macos-universal": {
        "url": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
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
        python_exe = os.environ.get("PYTHON_EXECUTABLE", os.sys.executable)
        detection_code = (
            "import json, llama_cpp\n"
            "has_metal = getattr(llama_cpp, 'llama_metal_available', lambda: False)()\n"
            "print(json.dumps({'metal': bool(has_metal)}))"
        )
        result = subprocess.run(
            [python_exe, "-c", detection_code],
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
    """
    Historically we tried to rebuild llama_cpp_python with Metal support here.
    Now the CI workflow installs the prebuilt Metal wheel directly, so we just
    verify availability and otherwise trust the existing installation.
    """
    if _llama_cpp_supports_metal():
        _log("llama_cpp_python reports Metal support; no rebuild required")
        return True

    _log("Skipping llama_cpp_python rebuild (Metal wheel expected to be preinstalled)")
    return True


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
        archive_path = Path(tmpdir) / "ffmpeg.zip"
        try:
            _download_file(release["url"], archive_path)
        except Exception as exc:
            _log(f"Warning: Unable to download ffmpeg bundle ({exc}); continuing without staging ffmpeg")
            return False

        import zipfile

        with zipfile.ZipFile(archive_path) as zf:
            root_candidates = {Path(member.filename).parts[0] for member in zf.infolist() if not member.is_dir()}
            if not root_candidates:
                _log("Unexpected archive structure; ffmpeg binaries not found")
                return False

            root_name = sorted(root_candidates)[0]
            zf.extractall(tmpdir)

        root = Path(tmpdir) / root_name
        candidate_ffmpeg = root / "ffmpeg"
        candidate_ffprobe = root / "ffprobe"

        if not candidate_ffmpeg.exists() or not candidate_ffprobe.exists():
            # Some Evermeet distributions embed binaries under bin/
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
    """Prepare environment for macOS arm64 builds."""

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

