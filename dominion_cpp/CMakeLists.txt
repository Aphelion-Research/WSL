cmake_minimum_required(VERSION 3.20)
project(dominion VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(DOMINION_BUILD_TESTS "Build tests" ON)
option(DOMINION_ENABLE_ONNX "Enable ONNX Runtime inference" OFF)

# Compiler flags
add_compile_options(-O3 -march=native -Wall -Wextra -Wpedantic)

# OpenMP
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    add_compile_options(${OpenMP_CXX_FLAGS})
endif()

# Dependencies via FetchContent
include(FetchContent)

FetchContent_Declare(json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
    URL_HASH SHA256=d6c65aca6b1ed68e7a182f4757f0f1c0e0c4f89d8e842e16f1b03c2215d91e28
)

FetchContent_Declare(httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.18.6
)

FetchContent_Declare(websocketpp
    GIT_REPOSITORY https://github.com/zaphoyd/websocketpp.git
    GIT_TAG 0.8.2
)

FetchContent_MakeAvailable(json httplib)
FetchContent_GetProperties(websocketpp)
if(NOT websocketpp_POPULATED)
    FetchContent_Populate(websocketpp)
endif()

# System dependencies
find_package(OpenSSL REQUIRED)
find_package(SQLite3)
if(NOT SQLite3_FOUND)
    find_library(SQLITE3_LIB sqlite3)
    find_path(SQLITE3_INCLUDE sqlite3.h)
    add_library(SQLite::SQLite3 INTERFACE IMPORTED)
    target_link_libraries(SQLite::SQLite3 INTERFACE ${SQLITE3_LIB})
    target_include_directories(SQLite::SQLite3 INTERFACE ${SQLITE3_INCLUDE})
endif()

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
    src/features/store.cpp
    src/features/price.cpp
    src/features/microstructure.cpp
    src/features/crossasset.cpp
    src/features/macro.cpp
    src/features/regime.cpp
    src/features/calendar.cpp
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
    ${websocketpp_SOURCE_DIR}
)

target_link_libraries(dominion_core PUBLIC
    nlohmann_json::nlohmann_json
    httplib::httplib
    OpenSSL::SSL
    OpenSSL::Crypto
    SQLite::SQLite3
    pthread
)

if(OpenMP_CXX_FOUND)
    target_link_libraries(dominion_core PUBLIC OpenMP::OpenMP_CXX)
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

# Install
install(TARGETS dominion_daemon dominion_cli RUNTIME DESTINATION bin)

# Tests
if(DOMINION_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
