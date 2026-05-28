# Dominion C++ Build

Build commands:

```bash
cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ragd/build -j$(nproc)
ctest --test-dir ragd/build --output-on-failure
```

CMake options:

- `DOMINION_BUILD_TESTS=ON`
- `DOMINION_BUILD_TOOLS=ON`
- `DOMINION_ENABLE_WARNINGS_AS_ERRORS=OFF`
- `DOMINION_USE_SYSTEM_SQLITE=ON`

Dependency pinning:

- `nlohmann_json` v3.11.3 archive SHA-256: `d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d`
- `cpp-httplib` v0.18.6 archive SHA-256: `8900747bba3dda8007f1876175be699036e09e4a25ceeab51196d9365bf1993a`

Current local detection:

- OpenSSL found via CMake `find_package(OpenSSL REQUIRED)`.
- SQLite found via `find_library` at `/usr/lib/x86_64-linux-gnu/libsqlite3.so.0` in the current WSL environment.

Offline note:

- The build remains pinned, but a clean machine without cached FetchContent archives still needs access to the pinned GitHub archives unless dependencies are pre-populated.

