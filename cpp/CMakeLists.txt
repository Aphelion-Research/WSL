cmake_minimum_required(VERSION 3.20)
project(hydra_features CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -ffast-math -Wall")

find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
endif()

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG)

if(NOT pybind11_FOUND)
    # Fallback: use pip-installed pybind11
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -m pybind11 --cmakedir
        OUTPUT_VARIABLE pybind11_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    find_package(pybind11 CONFIG PATHS ${pybind11_DIR})
endif()

if(pybind11_FOUND)
    # Build feature kernels module
    pybind11_add_module(hydra_kernels
        kernels/module.cpp
        kernels/rolling.cpp
        kernels/technical.cpp
        kernels/microstructure.cpp
        kernels/statistical.cpp
    )

    if(OpenMP_CXX_FOUND)
        target_link_libraries(hydra_kernels PRIVATE OpenMP::OpenMP_CXX)
    endif()

    # Install to dominion/features/
    install(TARGETS hydra_kernels
            LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../dominion/features)
else()
    message(WARNING "pybind11 not found. C++ kernels will not be built. Install: pip install pybind11")
endif()
