"""Hardware probe for dominion_loader.

Reports CPU count, RAM, GPU presence, and GPU VRAM.
Agent 2 reads this to choose model strategy (4GB VRAM constraint).

INTERFACE(agent-1): hw_probe() -> HardwareProfile  (stable, consumed by Agent 2)
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class HardwareProfile:
    """Hardware profile for this machine.

    INTERFACE(agent-1): All fields present. New fields are optional and additive.
    """
    cpu_count: int
    ram_bytes: int
    gpu_present: bool
    gpu_name: Optional[str]
    gpu_vram_bytes: Optional[int]
    platform: str       # "linux", "darwin", "windows"
    hostname: str


def hw_probe() -> HardwareProfile:
    """Return hardware profile for this machine.

    Tolerates missing GPU gracefully — gpu_present=False, gpu_vram_bytes=None.
    """
    import platform
    import socket

    cpu_count = os.cpu_count() or 1
    ram_bytes = _ram_bytes()
    gpu_name, gpu_vram_bytes = _gpu_info()

    return HardwareProfile(
        cpu_count=cpu_count,
        ram_bytes=ram_bytes,
        gpu_present=gpu_name is not None,
        gpu_name=gpu_name,
        gpu_vram_bytes=gpu_vram_bytes,
        platform=platform.system().lower(),
        hostname=socket.gethostname(),
    )


def hw_probe_json() -> dict:
    """Return hardware profile as a plain dict (JSON-serializable)."""
    return asdict(hw_probe())


# ---------------------------------------------------------------------------
# Internal probes
# ---------------------------------------------------------------------------
def _ram_bytes() -> int:
    """Read total RAM from /proc/meminfo (Linux) or fallback."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb * 1024
    except OSError:
        pass

    # Fallback via subprocess (macOS sysctl)
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=5)
        return int(out.strip())
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    return 0


def _gpu_info() -> tuple[Optional[str], Optional[int]]:
    """Detect GPU name and VRAM bytes.

    Tries nvidia-smi first, then AMD rocm-smi, then gives up gracefully.
    Returns (None, None) when no GPU is found.
    """
    # NVIDIA
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").strip()
        if out:
            parts = [p.strip() for p in out.split(",", 1)]
            name = parts[0] if parts else "NVIDIA GPU"
            vram_mb = int(parts[1]) if len(parts) > 1 else None
            vram_bytes = vram_mb * 1024 * 1024 if vram_mb else None
            return name, vram_bytes
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    # AMD via rocm-smi
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
        data = json.loads(out)
        # rocm-smi JSON structure varies; grab first card's VRAM
        for card_data in data.values():
            if isinstance(card_data, dict):
                for key, val in card_data.items():
                    if "vram" in key.lower() and "total" in key.lower():
                        return "AMD GPU", int(val)
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, json.JSONDecodeError, KeyError):
        pass

    return None, None
