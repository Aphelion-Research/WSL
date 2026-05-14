from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .registry import MODEL_REGISTRY, ProviderHealth, default_model_id


VRAM_SAFE_CEILING = 3_500_000_000


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
            return ExecutionPlan("retrieve_only", "none", "", 0, 0, True, 30, True, "Prior OOM recorded; generation disabled for this session.")
        if manual and env_model:
            return ExecutionPlan("generate", "ollama", env_model, 4096, 1, True, 30, True, "Manual governor override.")
        is_4gb_class = bool(profile.gpu_vram_bytes and profile.gpu_vram_bytes <= 4_500_000_000)
        if is_4gb_class and profile.gpu_busy:
            return ExecutionPlan("retrieve_only", "none", "", 0, 0, True, 30, True, "4 GB GPU is busy; retrieve-only is safer.")
        if is_4gb_class:
            candidate = _automatic_gpu_candidate(self.model_registry)
            if candidate is None:
                fallback = self.model_registry.get("retrieve_only_4gb", {})
                return ExecutionPlan(
                    "retrieve_only",
                    "none",
                    "",
                    0,
                    0,
                    True,
                    30,
                    True,
                    str(fallback.get("reason") or "No configured model fits the 3.5 GB ceiling for a 4 GB GPU."),
                )
            model = str(candidate["model_id"])
            return ExecutionPlan("generate", str(candidate.get("provider", "ollama")), model, 4096, 1, True, 30, True, f"Selected safe 4 GB profile by {profile.source} for {query_kind}.")
        model = default_model_id("cpu_safe")
        return ExecutionPlan("generate", "ollama", model, 2048 if not profile.gpu_vram_bytes else 4096, 1, True, 30, True, f"Selected by {profile.source} for {query_kind}.")


def _ram_bytes() -> int:
    try:
        with Path("/proc/meminfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return 0
    return 0


def _automatic_gpu_candidate(model_registry: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        profile
        for name, profile in model_registry.items()
        if profile.get("mode", "generate") == "generate"
        and profile.get("provider") not in {"none", None}
        and not profile.get("requires_manual")
        and int(profile.get("max_vram_bytes", 0)) > 0
        and int(profile.get("max_vram_bytes", 0)) <= VRAM_SAFE_CEILING
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: int(item.get("max_vram_bytes", 0)))[0]


def registry_truth(model_registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    registry = model_registry or MODEL_REGISTRY
    unsafe_safe = [
        {"profile": name, "max_vram_bytes": int(profile.get("max_vram_bytes", 0))}
        for name, profile in registry.items()
        if "safe" in name and int(profile.get("max_vram_bytes", 0)) > VRAM_SAFE_CEILING
    ]
    auto_gpu_candidate = _automatic_gpu_candidate(registry)
    status = "pass"
    detail = "registry has no unsafe safe profiles"
    if unsafe_safe:
        status = "fail"
        detail = "a profile named safe exceeds the VRAM safety ceiling"
    elif auto_gpu_candidate is None:
        status = "warn"
        detail = "no automatic 4 GB GPU generation profile is configured; retrieve-only fallback is explicit"
    return {
        "status": status,
        "detail": detail,
        "unsafe_safe_profiles": unsafe_safe,
        "auto_gpu_candidate": auto_gpu_candidate,
        "ceiling": VRAM_SAFE_CEILING,
    }


def doctor() -> dict[str, Any]:
    governor = Governor.default()
    profile = governor.probe()
    plan = governor.choose(profile)
    from .registry import provider
    truth = registry_truth()
    provider_health = (
        ProviderHealth(False, "none", [], plan.reason).to_dict()
        if plan.provider == "none"
        else provider(plan.provider).health().to_dict()
    )

    return {
        "ok": True,
        "profile": asdict(profile),
        "governor_plan": plan.to_dict(),
        "provider_health": provider_health,
        "registry_truth": truth,
    }
