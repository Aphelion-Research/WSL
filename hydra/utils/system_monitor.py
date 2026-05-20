"""System resource monitoring — CPU, RAM, GPU."""
from __future__ import annotations

import shutil


def get_system_stats() -> dict:
    stats = {
        "cpu_pct": None,
        "ram_pct": None,
        "ram_used_gb": None,
        "ram_total_gb": None,
        "disk_free_gb": None,
        "gpu_available": False,
        "gpu_name": None,
        "gpu_util_pct": None,
        "gpu_vram_used_gb": None,
        "gpu_vram_total_gb": None,
    }

    try:
        import psutil
        stats["cpu_pct"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        stats["ram_pct"] = mem.percent
        stats["ram_used_gb"] = round(mem.used / (1024**3), 1)
        stats["ram_total_gb"] = round(mem.total / (1024**3), 1)
    except ImportError:
        pass

    try:
        disk = shutil.disk_usage("/")
        stats["disk_free_gb"] = round(disk.free / (1024**3), 1)
    except OSError:
        pass

    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 4:
                stats["gpu_available"] = True
                stats["gpu_name"] = parts[0].strip()
                stats["gpu_util_pct"] = float(parts[1].strip())
                stats["gpu_vram_used_gb"] = round(float(parts[2].strip()) / 1024, 1)
                stats["gpu_vram_total_gb"] = round(float(parts[3].strip()) / 1024, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    return stats
