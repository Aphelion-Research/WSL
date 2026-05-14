#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

namespace dominion_native {

std::string sha256_bytes(const unsigned char *data, std::size_t size);
std::string sha256_string(const std::string &value);
std::string sha256_file(const std::filesystem::path &path);
std::string document_id(const std::string &repo_root, const std::string &relative_path);
std::string chunk_id(const std::string &repo_root, const std::string &relative_path, int line_start, int line_end, const std::string &content_hash);

}  // namespace dominion_native

