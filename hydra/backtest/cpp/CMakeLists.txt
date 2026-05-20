cmake_minimum_required(VERSION 3.20)
project(hydra_backtester CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -ffast-math")

find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
endif()

# ONNX Runtime
find_path(ONNXRUNTIME_INCLUDE onnxruntime_cxx_api.h
    PATHS /usr/local/include/onnxruntime
          $ENV{ONNXRUNTIME_ROOT}/include)
find_library(ONNXRUNTIME_LIB onnxruntime
    PATHS /usr/local/lib $ENV{ONNXRUNTIME_ROOT}/lib)

# DuckDB
find_library(DUCKDB_LIB duckdb PATHS /usr/local/lib)
find_path(DUCKDB_INCLUDE duckdb.hpp PATHS /usr/local/include)

add_executable(hydra_bt
    main.cpp
    backtester.cpp
    onnx_runner.cpp
    duckdb_loader.cpp
)

if(ONNXRUNTIME_INCLUDE AND ONNXRUNTIME_LIB)
    target_include_directories(hydra_bt PRIVATE ${ONNXRUNTIME_INCLUDE})
    target_link_libraries(hydra_bt PRIVATE ${ONNXRUNTIME_LIB})
    target_compile_definitions(hydra_bt PRIVATE HAS_ONNXRUNTIME)
endif()

if(DUCKDB_LIB AND DUCKDB_INCLUDE)
    target_include_directories(hydra_bt PRIVATE ${DUCKDB_INCLUDE})
    target_link_libraries(hydra_bt PRIVATE ${DUCKDB_LIB})
    target_compile_definitions(hydra_bt PRIVATE HAS_DUCKDB)
endif()

if(OpenMP_CXX_FOUND)
    target_link_libraries(hydra_bt PRIVATE OpenMP::OpenMP_CXX)
endif()
