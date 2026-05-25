#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "dominion/noise.hpp"
#include "dominion/information.hpp"
#include "dominion/multifractal.hpp"
#include "dominion/microstructure_advanced.hpp"
#include "dominion/jumps.hpp"
#include "dominion/stochastic_vol.hpp"
#include "dominion/causal.hpp"
#include "dominion/topology.hpp"
#include "dominion/network.hpp"
#include "dominion/copulas.hpp"
#include "dominion/recurrence.hpp"
#include "dominion/quantum.hpp"
#include "dominion/features.hpp"

namespace py = pybind11;

// Convert numpy array to PriceVec
dominion::PriceVec numpy_to_pricevec(py::array_t<double> arr) {
    py::buffer_info buf = arr.request();
    double *ptr = static_cast<double*>(buf.ptr);
    return dominion::PriceVec(ptr, ptr + buf.shape[0]);
}

// Convert PriceVec to numpy array
py::array_t<double> pricevec_to_numpy(const dominion::PriceVec& vec) {
    return py::array_t<double>(vec.size(), vec.data());
}

PYBIND11_MODULE(dominion_features, m) {
    m.doc() = "Dominion C++ feature engineering library";

    // ========== NOISE DECOMPOSITION ==========
    py::module_ noise = m.def_submodule("noise", "Noise decomposition features");

    py::class_<dominion::noise::SSAResult>(noise, "SSAResult")
        .def_readonly("components", &dominion::noise::SSAResult::components)
        .def_readonly("singular_values", &dominion::noise::SSAResult::singular_values)
        .def_readonly("explained_variance", &dominion::noise::SSAResult::explained_variance)
        .def_readonly("trend", &dominion::noise::SSAResult::trend)
        .def_readonly("noise", &dominion::noise::SSAResult::noise);

    py::class_<dominion::noise::EMDResult>(noise, "EMDResult")
        .def_readonly("imfs", &dominion::noise::EMDResult::imfs)
        .def_readonly("residual", &dominion::noise::EMDResult::residual)
        .def_readonly("frequencies", &dominion::noise::EMDResult::frequencies)
        .def_readonly("energies", &dominion::noise::EMDResult::energies);

    py::class_<dominion::noise::VMDResult>(noise, "VMDResult")
        .def_readonly("modes", &dominion::noise::VMDResult::modes)
        .def_readonly("center_frequencies", &dominion::noise::VMDResult::center_frequencies)
        .def_readonly("bandwidths", &dominion::noise::VMDResult::bandwidths);

    noise.def("compute_ssa", [](py::array_t<double> prices, int window_length, int n_components) {
        return dominion::noise::compute_ssa(numpy_to_pricevec(prices), window_length, n_components);
    }, py::arg("prices"), py::arg("window_length"), py::arg("n_components"));

    noise.def("compute_emd", [](py::array_t<double> prices, int max_imfs) {
        return dominion::noise::compute_emd(numpy_to_pricevec(prices), max_imfs);
    }, py::arg("prices"), py::arg("max_imfs") = 10);

    noise.def("compute_vmd", [](py::array_t<double> prices, int n_modes, double alpha) {
        return dominion::noise::compute_vmd(numpy_to_pricevec(prices), n_modes, alpha);
    }, py::arg("prices"), py::arg("n_modes"), py::arg("alpha") = 2000.0);

    noise.def("adaptive_denoise", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::noise::adaptive_denoise(numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 60);

    // ========== INFORMATION THEORY ==========
    py::module_ info = m.def_submodule("information", "Information theory features");

    info.def("compute_permutation_entropy", [](py::array_t<double> prices, int embed_dim, int delay, int window) {
        return pricevec_to_numpy(dominion::information::compute_permutation_entropy(
            numpy_to_pricevec(prices), embed_dim, delay, window));
    }, py::arg("prices"), py::arg("embed_dim") = 3, py::arg("delay") = 1, py::arg("window") = 100);

    info.def("compute_sample_entropy", [](py::array_t<double> prices, int m, double r, int window) {
        return pricevec_to_numpy(dominion::information::compute_sample_entropy(
            numpy_to_pricevec(prices), m, r, window));
    }, py::arg("prices"), py::arg("m") = 2, py::arg("r") = 0.2, py::arg("window") = 100);

    info.def("compute_transfer_entropy", [](py::array_t<double> source, py::array_t<double> target,
                                            int n_bins, int lag, int window) {
        return pricevec_to_numpy(dominion::information::compute_transfer_entropy(
            numpy_to_pricevec(source), numpy_to_pricevec(target), n_bins, lag, window));
    }, py::arg("source"), py::arg("target"), py::arg("n_bins") = 10, py::arg("lag") = 1, py::arg("window") = 252);

    info.def("compute_mutual_information", [](py::array_t<double> x, py::array_t<double> y,
                                              int n_bins, int window) {
        return pricevec_to_numpy(dominion::information::compute_mutual_information(
            numpy_to_pricevec(x), numpy_to_pricevec(y), n_bins, window));
    }, py::arg("x"), py::arg("y"), py::arg("n_bins") = 10, py::arg("window") = 252);

    info.def("compute_lz_complexity", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::information::compute_lz_complexity(
            numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 100);

    // ========== MULTIFRACTAL ==========
    py::module_ mf = m.def_submodule("multifractal", "Multifractal analysis");

    py::class_<dominion::multifractal::MFDFAResult>(mf, "MFDFAResult")
        .def_readonly("q_orders", &dominion::multifractal::MFDFAResult::q_orders)
        .def_readonly("hurst_q", &dominion::multifractal::MFDFAResult::hurst_q)
        .def_readonly("tau_q", &dominion::multifractal::MFDFAResult::tau_q)
        .def_readonly("alpha", &dominion::multifractal::MFDFAResult::alpha)
        .def_readonly("f_alpha", &dominion::multifractal::MFDFAResult::f_alpha)
        .def_readonly("multifractal_width", &dominion::multifractal::MFDFAResult::multifractal_width);

    mf.def("compute_mfdfa", [](py::array_t<double> prices, std::vector<double> q_orders,
                                std::vector<int> scales) {
        return dominion::multifractal::compute_mfdfa(numpy_to_pricevec(prices), q_orders, scales);
    }, py::arg("prices"), py::arg("q_orders"), py::arg("scales"));

    mf.def("compute_hurst_rs", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::multifractal::compute_hurst_rs(
            numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 252);

    mf.def("compute_fractal_dimension", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::multifractal::compute_fractal_dimension(
            numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 252);

    // ========== MICROSTRUCTURE ==========
    py::module_ micro = m.def_submodule("microstructure", "Microstructure noise models");

    micro.def("compute_hansen_lunde_rv", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::microstructure::compute_hansen_lunde_rv(
            numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 60);

    micro.def("compute_tsrv", [](py::array_t<double> prices, int fast_scale, int slow_scale, int window) {
        return pricevec_to_numpy(dominion::microstructure::compute_tsrv(
            numpy_to_pricevec(prices), fast_scale, slow_scale, window));
    }, py::arg("prices"), py::arg("fast_scale") = 1, py::arg("slow_scale") = 5, py::arg("window") = 60);

    micro.def("estimate_efficient_price", [](py::array_t<double> prices, int window) {
        return pricevec_to_numpy(dominion::microstructure::estimate_efficient_price(
            numpy_to_pricevec(prices), window));
    }, py::arg("prices"), py::arg("window") = 60);

    // ========== HIGH-LEVEL API ==========
    m.def("compute_all_features", [](py::array_t<double> prices, int n_threads) {
        // TODO: Orchestrate all feature computation
        // For now, return empty dict
        py::dict features;
        return features;
    }, py::arg("prices"), py::arg("n_threads") = 20,
    "Compute all 2000+ features in one call (batch mode)");

    m.def("version", []() {
        return "2.0.0-alpha";
    });
}
