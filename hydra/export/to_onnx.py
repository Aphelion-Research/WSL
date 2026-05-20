"""Export models to ONNX format."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from hydra.config import ARTIFACTS


def export_sklearn_to_onnx(
    model,
    n_features: int,
    output_path: Path,
    model_name: str = "model",
) -> Path:
    """Export sklearn model to ONNX via skl2onnx."""
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    initial_types = [("X", FloatTensorType([None, n_features]))]
    onnx_model = convert_sklearn(model, model_name, initial_types, target_opset=17)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    return output_path


def export_lgbm_to_onnx(model, n_features: int, output_path: Path) -> Path:
    """Export LightGBM to ONNX via onnxmltools."""
    import onnxmltools
    from onnxmltools.convert.common.data_types import FloatTensorType

    initial_types = [("X", FloatTensorType([None, n_features]))]
    onnx_model = onnxmltools.convert_lightgbm(model, initial_types=initial_types)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    return output_path


def export_xgb_to_onnx(model, n_features: int, output_path: Path) -> Path:
    """Export XGBoost to ONNX via onnxmltools."""
    import onnxmltools
    from onnxmltools.convert.common.data_types import FloatTensorType

    initial_types = [("X", FloatTensorType([None, n_features]))]
    onnx_model = onnxmltools.convert_xgboost(model, initial_types=initial_types)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    return output_path


def export_catboost_to_onnx(model, output_path: Path) -> Path:
    """Export CatBoost to ONNX via native export."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output_path), format="onnx")
    return output_path


def export_pytorch_to_onnx(
    model,
    input_shape: tuple,
    output_path: Path,
) -> Path:
    """Export PyTorch model to ONNX."""
    import torch

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy = torch.randn(*input_shape)
    torch.onnx.export(
        model, dummy, str(output_path),
        opset_version=17,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )
    return output_path
