"""Tests for ONNX export and quantisation."""
import numpy as np
import pytest

from hydra.config import ARTIFACTS


def test_fuse_onnx_roundtrip():
    """Build a fused ONNX graph and verify inference."""
    try:
        import onnx
        import onnxruntime as ort
    except ImportError:
        pytest.skip("onnx/onnxruntime not installed")

    from hydra.export.fuse import fuse_ensemble_onnx

    n_features = 12
    weights = np.random.RandomState(42).randn(n_features).astype(np.float32)
    bias = 0.1

    path = fuse_ensemble_onnx([], weights, bias)
    assert path.exists()

    sess = ort.InferenceSession(str(path))
    X = np.random.RandomState(42).randn(5, n_features).astype(np.float32)
    result = sess.run(None, {"X": X})[0]

    expected = 1.0 / (1.0 + np.exp(-(X @ weights.reshape(-1, 1) + bias)))
    np.testing.assert_allclose(result, expected, atol=1e-5)

    path.unlink()


def test_quantize_preserves_accuracy():
    """Quantized model should be close to float model."""
    try:
        import onnx
        import onnxruntime as ort
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError:
        pytest.skip("onnx/onnxruntime not installed")

    from hydra.export.fuse import fuse_ensemble_onnx
    from hydra.export.quantize import quantize_model

    n_features = 12
    weights = np.random.RandomState(42).randn(n_features).astype(np.float32)
    bias = 0.0

    float_path = fuse_ensemble_onnx([], weights, bias)
    probe = np.random.RandomState(42).randn(100, n_features).astype(np.float32)

    quant_path = quantize_model(float_path, probe_data=probe)
    assert quant_path.exists()

    float_sess = ort.InferenceSession(str(float_path))
    quant_sess = ort.InferenceSession(str(quant_path))

    float_out = float_sess.run(None, {"X": probe})[0]
    quant_out = quant_sess.run(None, {"X": probe})[0]

    max_diff = np.max(np.abs(float_out - quant_out))
    assert max_diff < 0.01

    float_path.unlink()
    quant_path.unlink()
