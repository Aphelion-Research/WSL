cmake_minimum_required(VERSION 3.20)
project(ragd VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
set(FETCHCONTENT_BASE_DIR "${CMAKE_SOURCE_DIR}/vendor" CACHE PATH "FetchContent dependency cache")

FetchContent_Declare(
  nlohmann_json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
  URL_HASH SHA256=4499d69450302b11565e31f4791e84dfcc5c1fd0585f6756616492d52f6c91d8
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(nlohmann_json)

FetchContent_Declare(
  cpp_httplib
  URL https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.18.6.tar.gz
  URL_HASH SHA256=93d40cc1112423bc548ba3a0ce0f69aae2ad590b1713d80d238cb05490795493
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(cpp_httplib)

# Use pkg-config or find_library for multiarch-aware SQLite discovery
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
  pkg_check_modules(SQLITE3 QUIET sqlite3)
endif()
if(SQLITE3_FOUND)
  set(SQLITE3_LIBRARY ${SQLITE3_LINK_LIBRARIES})
else()
  find_library(SQLITE3_LIBRARY NAMES sqlite3)
  if(NOT SQLITE3_LIBRARY)
    message(FATAL_ERROR "Could not find libsqlite3. Install libsqlite3-dev.")
  endif()
endif()

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
target_link_libraries(ragd_lib PUBLIC nlohmann_json::nlohmann_json ${SQLITE3_LIBRARY})

if(TARGET httplib::httplib)
  target_link_libraries(ragd_lib PUBLIC httplib::httplib)
else()
  target_include_directories(ragd_lib PUBLIC ${cpp_httplib_SOURCE_DIR})
endif()

add_executable(ragd src/main.cpp)
target_link_libraries(ragd PRIVATE ragd_lib)

install(TARGETS ragd RUNTIME DESTINATION bin)

enable_testing()
add_subdirectory(tests)
