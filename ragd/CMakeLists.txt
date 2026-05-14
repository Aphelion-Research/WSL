cmake_minimum_required(VERSION 3.20)
project(ragd VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DOMINION_BUILD_TESTS "Build Dominion native tests" ON)
option(DOMINION_BUILD_TOOLS "Build Dominion native CLI tools" ON)
option(DOMINION_ENABLE_WARNINGS_AS_ERRORS "Treat warnings as errors" OFF)
option(DOMINION_USE_SYSTEM_SQLITE "Use system SQLite" ON)

include(FetchContent)
set(FETCHCONTENT_BASE_DIR "${CMAKE_SOURCE_DIR}/vendor" CACHE PATH "FetchContent dependency cache")

FetchContent_Declare(
  nlohmann_json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
  URL_HASH SHA256=d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(nlohmann_json)

FetchContent_Declare(
  cpp_httplib
  URL https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.18.6.tar.gz
  URL_HASH SHA256=8900747bba3dda8007f1876175be699036e09e4a25ceeab51196d9365bf1993a
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(cpp_httplib)

find_package(OpenSSL REQUIRED)

# Use pkg-config or find_library for multiarch-aware SQLite discovery
if(DOMINION_USE_SYSTEM_SQLITE)
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(SQLITE3 QUIET sqlite3)
  endif()
  if(SQLITE3_FOUND)
    set(SQLITE3_LIBRARY ${SQLITE3_LINK_LIBRARIES})
    set(DOMINION_SQLITE_DETECTION "pkg-config:${SQLITE3_VERSION}")
  else()
    find_library(SQLITE3_LIBRARY NAMES sqlite3)
    if(NOT SQLITE3_LIBRARY)
      message(FATAL_ERROR "Could not find libsqlite3. Install libsqlite3-dev or provide a system SQLite library.")
    endif()
    set(DOMINION_SQLITE_DETECTION "find_library:${SQLITE3_LIBRARY}")
  endif()
else()
  message(FATAL_ERROR "DOMINION_USE_SYSTEM_SQLITE=OFF is not implemented; vendored SQLite is intentionally not fetched at configure time.")
endif()

add_library(dominion_native
  src/native/content_hash.cpp
  src/native/path_normalizer.cpp
  src/native/ignore_policy.cpp
  src/native/file_classifier.cpp
  src/native/scan_plan.cpp
  src/native/manifest_store.cpp
  src/native/vault_doctor.cpp
  src/native/doctor.cpp
  src/native/forbidden_tokens.cpp
  src/native/agent_locks.cpp
  src/native/agent_conflicts.cpp
  src/native/report.cpp
)

target_include_directories(dominion_native PUBLIC include)
target_link_libraries(dominion_native PUBLIC nlohmann_json::nlohmann_json OpenSSL::Crypto ${SQLITE3_LIBRARY})

add_library(ragd_lib
  src/config.cpp
  src/storage.cpp
  src/bm25.cpp
  src/vector_store.cpp
  src/indexer.cpp
  src/watcher.cpp
  src/agent_memory.cpp
  src/todo_engine.cpp
  src/temporal.cpp
  src/session_bus.cpp
  src/intent_router.cpp
  src/dead_zone.cpp
  src/rag_engine.cpp
  src/http_api.cpp
  src/mcp_server.cpp
)

target_include_directories(ragd_lib PUBLIC include)
target_link_libraries(ragd_lib PUBLIC nlohmann_json::nlohmann_json dominion_native ${SQLITE3_LIBRARY})

if(TARGET httplib::httplib)
  target_link_libraries(ragd_lib PUBLIC httplib::httplib)
else()
  target_include_directories(ragd_lib PUBLIC ${cpp_httplib_SOURCE_DIR})
endif()

if(DOMINION_ENABLE_WARNINGS_AS_ERRORS)
  target_compile_options(dominion_native PRIVATE -Wall -Wextra -Werror)
  target_compile_options(ragd_lib PRIVATE -Wall -Wextra -Werror)
endif()

add_executable(ragd_daemon src/main.cpp)
target_link_libraries(ragd_daemon PRIVATE ragd_lib)
set_target_properties(ragd_daemon PROPERTIES OUTPUT_NAME ragd)

if(DOMINION_BUILD_TOOLS)
  add_executable(dominion-native tools/dominion_native_cli.cpp)
  add_executable(dominion-native-doctor tools/native_doctor_main.cpp)
  add_executable(dominion-native-scan tools/native_scan_main.cpp)
  add_executable(dominion-native-manifest tools/native_manifest_main.cpp)
  add_executable(dominion-native-vault-doctor tools/native_vault_doctor_main.cpp)
  target_link_libraries(dominion-native PRIVATE dominion_native)
  target_link_libraries(dominion-native-doctor PRIVATE dominion_native)
  target_link_libraries(dominion-native-scan PRIVATE dominion_native)
  target_link_libraries(dominion-native-manifest PRIVATE dominion_native)
  target_link_libraries(dominion-native-vault-doctor PRIVATE dominion_native)
endif()

install(TARGETS ragd_daemon RUNTIME DESTINATION bin)

message(STATUS "Dominion SQLite detection: ${DOMINION_SQLITE_DETECTION}")
message(STATUS "Dominion dependency hashes: nlohmann_json=d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d cpp_httplib=8900747bba3dda8007f1876175be699036e09e4a25ceeab51196d9365bf1993a")

if(DOMINION_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
