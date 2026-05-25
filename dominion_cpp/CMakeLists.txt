cmake_minimum_required(VERSION 3.20)
project(dominion VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(DOMINION_BUILD_TESTS "Build tests" ON)
option(DOMINION_ENABLE_ONNX "Enable ONNX Runtime inference" OFF)
option(DOMINION_ENABLE_GPU "Enable DirectML GPU acceleration" ON)
option(DOMINION_USE_MKL "Use Intel MKL" ON)

# Compiler flags
add_compile_options(-O3 -march=native -ffast-math -Wall -Wextra -Wpedantic)

# OpenMP
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    add_compile_options(${OpenMP_CXX_FLAGS})
endif()

# Dependencies via FetchContent
include(FetchContent)

FetchContent_Declare(json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
    URL_HASH SHA256=d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)

FetchContent_Declare(httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.18.6
)

FetchContent_Declare(eigen
    GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
    GIT_TAG 3.4.0
    GIT_SHALLOW TRUE
)

FetchContent_Declare(pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.11.1
)

FetchContent_MakeAvailable(json httplib eigen pybind11)

# System dependencies
find_package(OpenSSL REQUIRED)

# QuantLib
find_package(QuantLib QUIET)
if(NOT QuantLib_FOUND)
    find_library(QUANTLIB_LIB QuantLib)
    find_path(QUANTLIB_INCLUDE ql/quantlib.hpp)
    if(QUANTLIB_LIB AND QUANTLIB_INCLUDE)
        add_library(QuantLib::QuantLib INTERFACE IMPORTED)
        target_link_libraries(QuantLib::QuantLib INTERFACE ${QUANTLIB_LIB})
        target_include_directories(QuantLib::QuantLib INTERFACE ${QUANTLIB_INCLUDE})
        set(QUANTLIB_AVAILABLE ON)
    endif()
else()
    set(QUANTLIB_AVAILABLE ON)
endif()

# FFTW3
find_package(FFTW3 QUIET)
if(NOT FFTW3_FOUND)
    find_library(FFTW3_LIB fftw3)
    find_path(FFTW3_INCLUDE fftw3.h)
    if(FFTW3_LIB AND FFTW3_INCLUDE)
        add_library(FFTW3::fftw3 INTERFACE IMPORTED)
        target_link_libraries(FFTW3::fftw3 INTERFACE ${FFTW3_LIB})
        target_include_directories(FFTW3::fftw3 INTERFACE ${FFTW3_INCLUDE})
        set(FFTW3_AVAILABLE ON)
    endif()
endif()

# Intel MKL (optional, fallback to OpenBLAS)
if(DOMINION_USE_MKL)
    find_package(MKL QUIET)
    if(MKL_FOUND)
        set(BLA_VENDOR Intel10_64lp)
        set(MKL_AVAILABLE ON)
    else()
        find_package(BLAS QUIET)
        find_package(LAPACK QUIET)
    endif()
else()
    find_package(BLAS QUIET)
    find_package(LAPACK QUIET)
endif()

# GUDHI (Topological Data Analysis)
find_path(GUDHI_INCLUDE gudhi/Simplex_tree.h PATHS /usr/include /usr/local/include)
if(GUDHI_INCLUDE)
    add_library(GUDHI::GUDHI INTERFACE IMPORTED)
    target_include_directories(GUDHI::GUDHI INTERFACE ${GUDHI_INCLUDE})
    set(GUDHI_AVAILABLE ON)
endif()

# igraph (network analysis)
find_library(IGRAPH_LIB igraph)
find_path(IGRAPH_INCLUDE igraph/igraph.h)
if(IGRAPH_LIB AND IGRAPH_INCLUDE)
    add_library(igraph::igraph INTERFACE IMPORTED)
    target_link_libraries(igraph::igraph INTERFACE ${IGRAPH_LIB})
    target_include_directories(igraph::igraph INTERFACE ${IGRAPH_INCLUDE})
    set(IGRAPH_AVAILABLE ON)
endif()

# ITensor (tensor networks)
find_library(ITENSOR_LIB itensor)
find_path(ITENSOR_INCLUDE itensor/all.h)
if(ITENSOR_LIB AND ITENSOR_INCLUDE)
    add_library(ITensor::ITensor INTERFACE IMPORTED)
    target_link_libraries(ITensor::ITensor INTERFACE ${ITENSOR_LIB})
    target_include_directories(ITensor::ITensor INTERFACE ${ITENSOR_INCLUDE})
    set(ITENSOR_AVAILABLE ON)
endif()

# DirectML (GPU acceleration via WSL)
if(DOMINION_ENABLE_GPU)
    find_library(DIRECTML_LIB DirectML PATHS /usr/lib/wsl/lib)
    if(DIRECTML_LIB)
        add_library(DirectML::DirectML INTERFACE IMPORTED)
        target_link_libraries(DirectML::DirectML INTERFACE ${DIRECTML_LIB})
        set(DIRECTML_AVAILABLE ON)
    endif()
endif()

# SQLite3 (link directly against .so.0 if dev package not installed)
set(SQLITE3_LIB "/usr/lib/x86_64-linux-gnu/libsqlite3.so.0")
set(SQLITE3_INCLUDE "/usr/include")
add_library(SQLite::SQLite3 INTERFACE IMPORTED)
target_link_libraries(SQLite::SQLite3 INTERFACE ${SQLITE3_LIB})
target_include_directories(SQLite::SQLite3 INTERFACE ${SQLITE3_INCLUDE})

# ONNX Runtime (optional)
if(DOMINION_ENABLE_ONNX)
    find_package(onnxruntime QUIET)
    if(NOT onnxruntime_FOUND)
        find_library(ONNXRUNTIME_LIB onnxruntime)
        find_path(ONNXRUNTIME_INCLUDE onnxruntime_cxx_api.h PATH_SUFFIXES onnxruntime)
        if(ONNXRUNTIME_LIB AND ONNXRUNTIME_INCLUDE)
            add_library(onnxruntime::onnxruntime INTERFACE IMPORTED)
            target_link_libraries(onnxruntime::onnxruntime INTERFACE ${ONNXRUNTIME_LIB})
            target_include_directories(onnxruntime::onnxruntime INTERFACE ${ONNXRUNTIME_INCLUDE})
            set(ONNXRUNTIME_AVAILABLE ON)
        endif()
    else()
        set(ONNXRUNTIME_AVAILABLE ON)
    endif()
endif()

# Core library
add_library(dominion_core STATIC
    src/pipeline/pipeline.cpp
    src/pipeline/config.cpp
    src/pipeline/schema.cpp
    src/sources/yahoo.cpp
    src/sources/fred.cpp
    src/sources/alphavantage.cpp
    src/sources/cot.cpp
    src/sources/mt5.cpp
    src/fusion/kalman.cpp
    src/fusion/bridge.cpp
    src/fusion/conflict.cpp
    src/features/primitives.cpp
    src/features/store.cpp
    src/features/price.cpp
    src/features/microstructure.cpp
    src/features/crossasset.cpp
    src/features/macro.cpp
    src/features/regime.cpp
    src/features/calendar.cpp
    src/features/ml_features.cpp
    src/features/signal_processing.cpp
    src/features/orderbook_features.cpp
    src/features/crossasset_advanced.cpp
    src/features/causal_features.cpp
    src/health/monitor.cpp
    src/health/anomaly.cpp
    src/health/report.cpp
    src/bus/client.cpp
    src/bus/publisher.cpp
    src/mt5/collector.cpp
    src/mt5/safety.cpp
)

target_include_directories(dominion_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(dominion_core PUBLIC
    nlohmann_json::nlohmann_json
    httplib::httplib
    OpenSSL::SSL
    OpenSSL::Crypto
    SQLite::SQLite3
    Eigen3::Eigen
    pthread
)

if(OpenMP_CXX_FOUND)
    target_link_libraries(dominion_core PUBLIC OpenMP::OpenMP_CXX)
endif()

if(QUANTLIB_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_QUANTLIB=1)
    target_link_libraries(dominion_core PUBLIC QuantLib::QuantLib)
endif()

if(FFTW3_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_FFTW3=1)
    target_link_libraries(dominion_core PUBLIC FFTW3::fftw3)
endif()

if(MKL_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_MKL=1)
    target_link_libraries(dominion_core PUBLIC MKL::MKL)
elseif(BLAS_FOUND AND LAPACK_FOUND)
    target_link_libraries(dominion_core PUBLIC ${BLAS_LIBRARIES} ${LAPACK_LIBRARIES})
endif()

if(GUDHI_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_GUDHI=1)
    target_link_libraries(dominion_core PUBLIC GUDHI::GUDHI)
endif()

if(IGRAPH_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_IGRAPH=1)
    target_link_libraries(dominion_core PUBLIC igraph::igraph)
endif()

if(ITENSOR_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_ITENSOR=1)
    target_link_libraries(dominion_core PUBLIC ITensor::ITensor)
endif()

if(DIRECTML_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_DIRECTML=1)
    target_link_libraries(dominion_core PUBLIC DirectML::DirectML)
endif()

if(DOMINION_ENABLE_ONNX AND ONNXRUNTIME_AVAILABLE)
    target_compile_definitions(dominion_core PUBLIC DOMINION_HAS_ONNX=1)
    target_link_libraries(dominion_core PUBLIC onnxruntime::onnxruntime)
endif()

# Main daemon
add_executable(dominion_daemon src/main.cpp)
target_link_libraries(dominion_daemon PRIVATE dominion_core)

# CLI tool
add_executable(dominion_cli src/cli.cpp)
target_link_libraries(dominion_cli PRIVATE dominion_core)

# Python bindings
pybind11_add_module(dominion_features bindings/python.cpp)
target_link_libraries(dominion_features PRIVATE dominion_core)

# Install
install(TARGETS dominion_daemon dominion_cli RUNTIME DESTINATION bin)
install(TARGETS dominion_features LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/python3/dist-packages)

# Tests
if(DOMINION_BUILD_TESTS AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt)
    enable_testing()
    add_subdirectory(tests)
endif()
