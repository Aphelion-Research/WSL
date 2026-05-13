from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .registry import MODEL_REGISTRY, default_model_id


@dataclass(frozen=True)
class HardwareProfile:
    gpu_vram_bytes: int = 0
    ram_bytes: int = 0
    gpu_busy: bool = False
    source: str = "TEMP_ADAPTER(agent-1): dominion_loader.hw_probe unavailable; remove fallback after Agent 1 interface is guaranteed."


@dataclass(frozen=True)
class ExecutionPlan:
    mode: str
    provider: str
    model_id: str
    ctx_len: int
    batch: int
    stream: bool
    timeout_s: int
    cpu_fallback: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Governor:
    def __init__(self, model_registry: dict[str, dict[str, Any]] | None = None, oom_seen: bool = False):
        self.model_registry = model_registry or MODEL_REGISTRY
        self.oom_seen = oom_seen

    @classmethod
    def default(cls) -> "Governor":
        return cls()

    @staticmethod
    def probe() -> HardwareProfile:
        try:
            from dominion_loader.api import hw_probe

            upstream = hw_probe()
            return HardwareProfile(
                gpu_vram_bytes=int(upstream.gpu_vram_bytes or 0),
                ram_bytes=int(upstream.ram_bytes or 0),
                gpu_busy=False,
                source="dominion_loader.hw_probe",
            )
        except Exception:
            pass
        env_vram = os.environ.get("DOMINION_GPU_VRAM_BYTES")
        if env_vram:
            return HardwareProfile(gpu_vram_bytes=int(env_vram), ram_bytes=_ram_bytes(), source="env")
        nvidia = shutil.which("nvidia-smi")
        if nvidia:
            try:
                output = subprocess.check_output([nvidia, "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"], text=True, timeout=2)
                total_mb, used_mb = [int(part.strip()) for part in output.splitlines()[0].split(",")[:2]]
                return HardwareProfile(gpu_vram_bytes=total_mb * 1024 * 1024, ram_bytes=_ram_bytes(), gpu_busy=used_mb / max(1, total_mb) > 0.85, source="nvidia-smi")
            except Exception:
                pass
        return HardwareProfile(ram_bytes=_ram_bytes())

    def choose(self, profile: HardwareProfile, query_kind: str = "ask") -> ExecutionPlan:
        manual = os.environ.get("DOMINION_GOVERNOR") == "manual"
        env_model = os.environ.get("DOMINION_LLM_MODEL")
        if self.oom_seen:
            return ExecutionPlan("retrieve_only", "ollama", "", 0, 0, True, 30, True, "Prior OOM recorded; generation disabled for this session.")
        if manual and env_model:
            return ExecutionPlan("generate", "ollama", env_model, 4096, 1, True, 30, True, "Manual governor override.")
        is_4gb_class = bool(profile.gpu_vram_bytes and profile.gpu_vram_bytes <= 4_500_000_000)
        if is_4gb_class and profile.gpu_busy:
            return ExecutionPlan("retrieve_only", "ollama", "", 0, 0, True, 30, True, "4 GB GPU is busy; retrieve-only is safer.")
        model = default_model_id("gpu_4gb_safe" if profile.gpu_vram_bytes else "cpu_safe")
        max_vram = int(self.model_registry["gpu_4gb_safe"]["max_vram_bytes"])
        if is_4gb_class and max_vram > 3_500_000_000:
            return ExecutionPlan("retrieve_only", "ollama", "", 0, 0, True, 30, True, "No configured model fits the 3.5 GB ceiling for a 4 GB GPU.")
        return ExecutionPlan("generate", "ollama", model, 4096 if profile.gpu_vram_bytes else 2048, 1, True, 30, True, f"Selected by {profile.source} for {query_kind}.")


def _ram_bytes() -> int:
    try:
        with Path("/proc/meminfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return 0
    return 0


def doctor() -> dict[str, Any]:
    governor = Governor.default()
    profile = governor.probe()
    plan = governor.choose(profile)
    from .registry import provider

    return {
        "ok": True,
        "profile": asdict(profile),
        "governor_plan": plan.to_dict(),
        "provider_health": provider(plan.provider).health().to_dict(),
    }
