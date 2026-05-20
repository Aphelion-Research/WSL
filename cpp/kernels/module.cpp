#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "rolling.hpp"
#include "technical.hpp"
#include "microstructure.hpp"
#include "statistical.hpp"

namespace py = pybind11;

PYBIND11_MODULE(hydra_kernels, m) {
    m.doc() = "HYDRA C++ feature kernels with point-in-time safety";

    // Rolling functions
    m.def("rolling_mean", &hydra::rolling_mean,
          py::arg("data"), py::arg("window"),
          "Compute rolling mean (point-in-time safe)");

    m.def("rolling_std", &hydra::rolling_std,
          py::arg("data"), py::arg("window"),
          "Compute rolling standard deviation");

    m.def("rolling_min", &hydra::rolling_min,
          py::arg("data"), py::arg("window"),
          "Compute rolling minimum");

    m.def("rolling_max", &hydra::rolling_max,
          py::arg("data"), py::arg("window"),
          "Compute rolling maximum");

    m.def("rolling_zscore", &hydra::rolling_zscore,
          py::arg("data"), py::arg("window"),
          "Compute rolling z-score");

    m.def("rolling_skew", &hydra::rolling_skew,
          py::arg("data"), py::arg("window"),
          "Compute rolling skewness");

    m.def("rolling_kurt", &hydra::rolling_kurt,
          py::arg("data"), py::arg("window"),
          "Compute rolling kurtosis (excess)");

    m.def("rolling_corr", &hydra::rolling_corr,
          py::arg("x"), py::arg("y"), py::arg("window"),
          "Compute rolling correlation between two series");

    // Technical indicators
    m.def("ema", &hydra::ema,
          py::arg("data"), py::arg("period"),
          "Compute Exponential Moving Average");

    m.def("rsi", &hydra::rsi,
          py::arg("data"), py::arg("period"),
          "Compute Relative Strength Index");

    m.def("atr", &hydra::atr,
          py::arg("high"), py::arg("low"), py::arg("close"), py::arg("period"),
          "Compute Average True Range");

    m.def("realized_volatility", &hydra::realized_volatility,
          py::arg("data"), py::arg("period"),
          "Compute realized volatility from close prices");

    // Bollinger Bands (return struct)
    py::class_<hydra::BollingerBands>(m, "BollingerBands")
        .def_readonly("upper", &hydra::BollingerBands::upper)
        .def_readonly("middle", &hydra::BollingerBands::middle)
        .def_readonly("lower", &hydra::BollingerBands::lower)
        .def_readonly("width", &hydra::BollingerBands::width);

    m.def("bollinger_bands", &hydra::bollinger_bands,
          py::arg("data"), py::arg("period"), py::arg("num_std") = 2.0f,
          "Compute Bollinger Bands");

    // Microstructure features
    m.def("candle_body", &hydra::candle_body,
          py::arg("open"), py::arg("close"),
          "Compute candle body size (close - open)");

    m.def("candle_upper_wick", &hydra::candle_upper_wick,
          py::arg("open"), py::arg("high"), py::arg("close"),
          "Compute upper wick size");

    m.def("candle_lower_wick", &hydra::candle_lower_wick,
          py::arg("open"), py::arg("low"), py::arg("close"),
          "Compute lower wick size");

    m.def("candle_range", &hydra::candle_range,
          py::arg("high"), py::arg("low"),
          "Compute candle range (high - low)");

    m.def("candle_body_ratio", &hydra::candle_body_ratio,
          py::arg("open"), py::arg("high"), py::arg("low"), py::arg("close"),
          "Compute body ratio (body / range)");

    m.def("candle_close_loc", &hydra::candle_close_loc,
          py::arg("high"), py::arg("low"), py::arg("close"),
          "Compute close location within range [0, 1]");

    // Statistical functions
    m.def("autocorr", &hydra::autocorr,
          py::arg("data"), py::arg("lag"),
          "Compute autocorrelation at given lag");

    m.def("rolling_autocorr", &hydra::rolling_autocorr,
          py::arg("data"), py::arg("window"), py::arg("lag"),
          "Compute rolling autocorrelation");

    m.def("rolling_quantile", &hydra::rolling_quantile,
          py::arg("data"), py::arg("window"), py::arg("q"),
          "Compute rolling quantile");
}
