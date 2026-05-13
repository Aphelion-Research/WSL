"""Tests for dominion_loader.hw_probe."""
from __future__ import annotations

import pytest
from dominion_loader.hw_probe import hw_probe, hw_probe_json, HardwareProfile


def test_hw_probe_returns_profile() -> None:
    profile = hw_probe()
    assert isinstance(profile, HardwareProfile)


def test_hw_probe_cpu_count_positive() -> None:
    profile = hw_probe()
    assert profile.cpu_count >= 1


def test_hw_probe_ram_bytes_positive() -> None:
    profile = hw_probe()
    assert profile.ram_bytes > 0, "Expected positive RAM bytes"


def test_hw_probe_platform_known() -> None:
    profile = hw_probe()
    assert profile.platform in ("linux", "darwin", "windows", "")


def test_hw_probe_gpu_fields_consistent() -> None:
    profile = hw_probe()
    if profile.gpu_present:
        assert profile.gpu_name is not None
    else:
        # gpu_present=False: vram_bytes may be None
        assert profile.gpu_present is False


def test_hw_probe_json_serializable() -> None:
    """hw_probe_json() must return a JSON-serializable dict."""
    import json
    data = hw_probe_json()
    assert isinstance(data, dict)
    # Must not raise
    serialized = json.dumps(data)
    assert "cpu_count" in serialized
    assert "ram_bytes" in serialized


def test_hw_probe_json_schema() -> None:
    """All required fields present in JSON output."""
    data = hw_probe_json()
    required = {"cpu_count", "ram_bytes", "gpu_present", "gpu_name", "gpu_vram_bytes", "platform", "hostname"}
    for key in required:
        assert key in data, f"Missing key: {key}"
