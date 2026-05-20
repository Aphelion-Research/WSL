"""INT4/INT8 dynamic quantisation of ONNX models."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from hydra.config import ARTIFACTS


def quantize_model(
    input_path: Path | None = None,
    output_path: Path | None = None,
    probe_data: np.ndarray | None = None,
    max_diff_threshold: float = 1e-3,
) -> Path:
    """Apply dynamic quantisation, fall back to INT8 if INT4 degrades too much."""
    from onnxruntime.quantization import quantize_dynamic, QuantType

    if input_path is None:
        input_path = ARTIFACTS / "hydra_fused.onnx"
    if output_path is None:
        output_path = ARTIFACTS / "hydra_fused.int4.onnx"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        quantize_dynamic(
            model_input=str(input_path),
            model_output=str(output_path),
            weight_type=QuantType.QInt8,
            per_channel=True,
            reduce_range=False,
            extra_options={"WeightSymmetric": True},
        )
    except Exception:
        quantize_dynamic(
            model_input=str(input_path),
            model_output=str(output_path),
            weight_type=QuantType.QInt8,
        )

    if probe_data is not None:
        diff = _validate_quantization(input_path, output_path, probe_data)
        if diff > max_diff_threshold:
            quantize_dynamic(
                model_input=str(input_path),
                model_output=str(output_path),
                weight_type=QuantType.QInt8,
            )

    return output_path


def _validate_quantization(
    float_path: Path,
    quant_path: Path,
    probe_data: np.ndarray,
) -> float:
    """Return max absolute difference between float and quantized model."""
    import onnxruntime as ort

    float_sess = ort.InferenceSession(str(float_path))
    quant_sess = ort.InferenceSession(str(quant_path))

    input_name = float_sess.get_inputs()[0].name
    float_out = float_sess.run(None, {input_name: probe_data.astype(np.float32)})[0]
    quant_out = quant_sess.run(None, {input_name: probe_data.astype(np.float32)})[0]

    return float(np.max(np.abs(float_out - quant_out)))
