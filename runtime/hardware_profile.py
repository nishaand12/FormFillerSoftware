"""Hardware capability detection and runtime heuristics.

This module centralises hardware detection so the rest of the application can
adapt behaviour (model selection, prompt token budgets, etc.) without needing
to know platform specifics.
"""

from __future__ import annotations

import functools
import os
import platform
from dataclasses import dataclass
from typing import Optional

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - psutil is shipped with the app
    psutil = None  # type: ignore


@dataclass(frozen=True)
class HardwareProfile:
    architecture: str
    physical_cores: int
    logical_cores: int
    memory_gb: float
    is_apple_silicon: bool
    is_rosetta: bool
    os_version: str
    metal_available: bool
    cuda_available: bool = False  # NVIDIA GPU support on Windows/Linux


def _detect_psutil_cores(default: int = 2) -> tuple[int, int]:
    if psutil:
        physical = psutil.cpu_count(logical=False) or default
        logical = psutil.cpu_count(logical=True) or physical
        return physical, logical
    logical = os.cpu_count() or default
    return default, logical


def _detect_memory_gb() -> float:
    if psutil:
        return round(psutil.virtual_memory().total / (1024**3), 2)
    try:
        import subprocess
        import sys
        
        if sys.platform == 'darwin':
            # macOS: use sysctl
            output = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            return round(int(output.strip()) / (1024**3), 2)
        elif sys.platform == 'win32':
            # Windows: use wmic (fallback if psutil not available)
            output = subprocess.check_output(
                ["wmic", "computersystem", "get", "totalphysicalmemory"],
                text=True
            )
            # Parse output - second line contains the value
            lines = output.strip().split('\n')
            if len(lines) >= 2:
                mem_bytes = int(lines[1].strip())
                return round(mem_bytes / (1024**3), 2)
        return 0.0
    except Exception:
        return 0.0


def _check_metal_available(is_apple_silicon: bool) -> bool:
    """Check if Metal (macOS) GPU acceleration is available."""
    if not is_apple_silicon:
        return False
    try:
        import llama_cpp  # type: ignore

        probe = getattr(llama_cpp, "llama_metal_available", None)
        if callable(probe):
            return bool(probe())
    except Exception:
        return False
    return False


def _check_cuda_available() -> bool:
    """Check if CUDA (NVIDIA GPU) acceleration is available on Windows/Linux."""
    try:
        import llama_cpp  # type: ignore
        
        # Check if llama-cpp-python was built with CUDA support
        # This is typically indicated by the presence of certain symbols
        if hasattr(llama_cpp, 'llama_backend_init'):
            # Try to detect NVIDIA GPU via environment or cuda library
            import subprocess
            import sys
            
            if sys.platform == 'win32':
                # On Windows, check for nvidia-smi
                try:
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            return False
    except Exception:
        return False
    return False


@functools.lru_cache(maxsize=1)
def get_hardware_profile() -> HardwareProfile:
    import sys
    
    architecture = platform.machine().lower()
    physical, logical = _detect_psutil_cores()
    memory_gb = _detect_memory_gb()
    
    # Get OS version based on platform
    if platform.system() == "Darwin":
        os_version = platform.mac_ver()[0]
    elif platform.system() == "Windows":
        os_version = platform.win32_ver()[0]
    else:
        os_version = platform.version()

    is_apple_silicon = architecture in {"arm64", "aarch64"} and platform.system() == "Darwin"
    is_rosetta = platform.system() == "Darwin" and architecture == "x86_64" and "arm64" in platform.platform()
    metal_available = _check_metal_available(is_apple_silicon)
    
    # Check for CUDA on Windows/Linux
    cuda_available = False
    if sys.platform in ('win32', 'linux'):
        cuda_available = _check_cuda_available()

    return HardwareProfile(
        architecture=architecture,
        physical_cores=physical,
        logical_cores=logical,
        memory_gb=memory_gb,
        is_apple_silicon=is_apple_silicon,
        is_rosetta=is_rosetta,
        os_version=os_version,
        metal_available=metal_available,
        cuda_available=cuda_available,
    )


def recommended_model_type(preferred: str = "qwen3-4b") -> str:
    profile = get_hardware_profile()

    if profile.memory_gb and profile.memory_gb < 12:
        return "qwen3-1.7b"

    # Check for GPU acceleration (Metal on macOS, CUDA on Windows/Linux)
    has_gpu = profile.metal_available or profile.cuda_available
    if not has_gpu and profile.memory_gb and profile.memory_gb < 16:
        return "qwen3-1.7b"

    return preferred


@dataclass(frozen=True)
class LlamaRuntimeConfig:
    n_ctx: int
    n_threads: int
    n_gpu_layers: int
    max_tokens: int


def _compute_token_budget(model_type: str, n_ctx: int, transcript_chars: Optional[int]) -> int:
    if model_type == "qwen3-4b":
        ceiling = min(1536, n_ctx - 512)
    else:
        ceiling = min(1024, n_ctx - 512)

    if transcript_chars is None:
        return ceiling

    dynamic = max(256, transcript_chars // 3)
    return min(dynamic, ceiling)


def get_llama_runtime_config(
    model_type: str,
    *,
    transcript_chars: Optional[int] = None,
    requested_max_tokens: Optional[int] = None,
) -> LlamaRuntimeConfig:
    profile = get_hardware_profile()

    # Determine GPU acceleration settings
    if profile.is_apple_silicon and profile.metal_available:
        # Apple Silicon with Metal - use all GPU layers
        n_gpu_layers = -1
        n_threads = max(2, profile.physical_cores)
        n_ctx = 4096 if model_type == "qwen3-4b" else 3072
    elif profile.cuda_available:
        # NVIDIA GPU with CUDA - use all GPU layers
        n_gpu_layers = -1
        n_threads = max(2, profile.physical_cores)
        n_ctx = 4096 if model_type == "qwen3-4b" else 3072
    else:
        # CPU-only mode
        n_gpu_layers = 0
        n_threads = min(max(2, profile.physical_cores), 6)
        n_ctx = 3072 if model_type == "qwen3-4b" else 2048

    budget = _compute_token_budget(model_type, n_ctx, transcript_chars)

    if requested_max_tokens is not None:
        max_tokens = max(128, min(requested_max_tokens, n_ctx - 128))
        max_tokens = min(max_tokens, budget)
    else:
        max_tokens = budget

    return LlamaRuntimeConfig(
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        max_tokens=max_tokens,
    )


