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
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(nlohmann_json)

FetchContent_Declare(
  cpp_httplib
  URL https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.18.6.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(cpp_httplib)

find_library(SQLITE3_LIBRARY NAMES sqlite3 libsqlite3.so.0)
if(NOT SQLITE3_LIBRARY AND EXISTS "/lib/x86_64-linux-gnu/libsqlite3.so.0")
  set(SQLITE3_LIBRARY "/lib/x86_64-linux-gnu/libsqlite3.so.0")
endif()
if(NOT SQLITE3_LIBRARY)
  message(FATAL_ERROR "Could not find libsqlite3 runtime library")
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
