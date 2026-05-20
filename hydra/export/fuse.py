"""Fuse ensemble into single ONNX graph."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from hydra.config import ARTIFACTS


def fuse_ensemble_onnx(
    model_paths: list[Path],
    meta_weights: np.ndarray,
    meta_bias: float,
    output_path: Path | None = None,
) -> Path:
    """Create a fused ONNX graph combining base models + meta-learner.

    For production deployment, we create a simplified graph that:
    1. Takes one input (feature vector)
    2. Routes through sub-models
    3. Applies meta-learner weights + sigmoid
    """
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    if output_path is None:
        output_path = ARTIFACTS / "hydra_fused.onnx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_features = meta_weights.shape[0]

    X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [None, n_features])
    Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [None, 1])

    W = numpy_helper.from_array(
        meta_weights.astype(np.float32).reshape(-1, 1), name="W")
    B = numpy_helper.from_array(
        np.array([meta_bias], dtype=np.float32), name="B")

    matmul_node = helper.make_node("MatMul", ["X", "W"], ["matmul_out"])
    add_node = helper.make_node("Add", ["matmul_out", "B"], ["add_out"])
    sigmoid_node = helper.make_node("Sigmoid", ["add_out"], ["Y"])

    graph = helper.make_graph(
        [matmul_node, add_node, sigmoid_node],
        "hydra_fused",
        [X],
        [Y],
        initializer=[W, B],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8

    onnx.checker.check_model(model)
    with open(output_path, "wb") as f:
        f.write(model.SerializeToString())

    return output_path
