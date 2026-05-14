#include "dominion_native/content_hash.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  assert(dominion_native::sha256_string("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-hash-test";
  std::filesystem::create_directories(dir);
  auto path = dir / "large.txt";
  {
    std::ofstream out(path);
    for (int i = 0; i < 10000; ++i) out << "dominion native hash\n";
  }
  auto h1 = dominion_native::sha256_file(path);
  auto h2 = dominion_native::sha256_file(path);
  assert(h1 == h2);
  assert(dominion_native::document_id("/repo", "a/b.cpp") == dominion_native::document_id("/repo", "a/b.cpp"));
  assert(dominion_native::chunk_id("/repo", "a/b.cpp", 1, 2, h1) != dominion_native::chunk_id("/repo", "a/b.cpp", 1, 2, h1 + "x"));
  return 0;
}

