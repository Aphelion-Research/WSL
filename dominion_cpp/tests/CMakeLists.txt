find_package(GTest QUIET)

if(NOT GTest_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
    )
    FetchContent_MakeAvailable(googletest)
endif()

add_executable(test_point_in_time_safety test_point_in_time_safety.cpp)
target_link_libraries(test_point_in_time_safety PRIVATE dominion_core GTest::gtest GTest::gtest_main)

add_test(NAME PointInTimeSafety COMMAND test_point_in_time_safety)
