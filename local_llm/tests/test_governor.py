from __future__ import annotations

from local_llm.governor import Governor, HardwareProfile


def test_4gb_profile_respects_vram_ceiling():
    plan = Governor().choose(HardwareProfile(gpu_vram_bytes=4_000_000_000, ram_bytes=8_000_000_000))
    assert plan.mode in {"generate", "retrieve_only"}
    if plan.mode == "generate":
        assert plan.ctx_len <= 4096


def test_governor_cpu_fallback_on_no_gpu():
    plan = Governor().choose(HardwareProfile(gpu_vram_bytes=0, ram_bytes=8_000_000_000))
    assert plan.cpu_fallback is True


def test_governor_degrades_after_oom():
    assert Governor(oom_seen=True).choose(HardwareProfile()).mode == "retrieve_only"
