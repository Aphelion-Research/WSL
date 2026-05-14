#include "dominion_native/file_classifier.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-classifier-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "src");
  auto cpp = dir / "src" / "x.cpp";
  std::ofstream(cpp) << "int main(){}\n";
  auto c = dominion_native::classify_file(cpp, "src/x.cpp", std::filesystem::file_size(cpp));
  assert(c.kind == "source");
  assert(c.language == "cpp");
  assert(!c.binary);
  auto bin = dir / "blob.bin";
  std::ofstream bout(bin, std::ios::binary);
  bout << "abc";
  bout.put('\0');
  bout << "def";
  bout.close();
  auto b = dominion_native::classify_file(bin, "blob.bin", std::filesystem::file_size(bin));
  assert(b.binary);
  auto gen = dominion_native::classify_file(cpp, "build/generated.cpp", std::filesystem::file_size(cpp));
  assert(gen.generated);
  return 0;
}

