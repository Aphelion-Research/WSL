from __future__ import annotations

from local_llm.governor import Governor, HardwareProfile, VRAM_SAFE_CEILING, registry_truth
from local_llm.registry import MODEL_REGISTRY


def test_4gb_profile_respects_vram_ceiling():
    plan = Governor().choose(HardwareProfile(gpu_vram_bytes=4_000_000_000, ram_bytes=8_000_000_000))
    assert plan.mode == "retrieve_only"
    assert plan.model_id == ""
    assert "3.5 GB" in plan.reason


def test_governor_cpu_fallback_on_no_gpu():
    plan = Governor().choose(HardwareProfile(gpu_vram_bytes=0, ram_bytes=8_000_000_000))
    assert plan.cpu_fallback is True
    assert plan.mode == "generate"


def test_governor_degrades_after_oom():
    assert Governor(oom_seen=True).choose(HardwareProfile()).mode == "retrieve_only"


def test_registry_has_no_unsafe_safe_profiles():
    for name, profile in MODEL_REGISTRY.items():
        if "safe" in name:
            assert int(profile.get("max_vram_bytes", 0)) <= VRAM_SAFE_CEILING


def test_manual_override_required_for_risky_4gb_model(monkeypatch):
    monkeypatch.delenv("DOMINION_GOVERNOR", raising=False)
    monkeypatch.setenv("DOMINION_LLM_MODEL", "manual-risky-model")
    automatic = Governor().choose(HardwareProfile(gpu_vram_bytes=4_000_000_000, ram_bytes=8_000_000_000))
    assert automatic.mode == "retrieve_only"

    monkeypatch.setenv("DOMINION_GOVERNOR", "manual")
    manual = Governor().choose(HardwareProfile(gpu_vram_bytes=4_000_000_000, ram_bytes=8_000_000_000))
    assert manual.mode == "generate"
    assert manual.model_id == "manual-risky-model"


def test_registry_truth_warns_when_no_safe_4gb_generation_model():
    truth = registry_truth()
    assert truth["status"] == "warn"
    assert truth["unsafe_safe_profiles"] == []


def test_governor_can_select_explicit_safe_gpu_candidate():
    registry = {
        "retrieve_only_4gb": MODEL_REGISTRY["retrieve_only_4gb"],
        "gpu_4gb_real_safe": {
            "model_id": "small-safe-model",
            "max_vram_bytes": 2_000_000_000,
            "provider": "ollama",
            "mode": "generate",
        },
    }
    plan = Governor(model_registry=registry).choose(HardwareProfile(gpu_vram_bytes=4_000_000_000, ram_bytes=8_000_000_000))
    assert plan.mode == "generate"
    assert plan.model_id == "small-safe-model"
