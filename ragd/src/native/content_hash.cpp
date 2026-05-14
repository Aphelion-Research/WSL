#include "dominion_native/content_hash.hpp"

#include <openssl/evp.h>

#include <array>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace dominion_native {
namespace {

std::string hex_digest(const unsigned char *digest, unsigned int len) {
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned int i = 0; i < len; ++i) out << std::setw(2) << static_cast<int>(digest[i]);
  return out.str();
}

class Sha256Ctx {
 public:
  Sha256Ctx() : ctx_(EVP_MD_CTX_new()) {
    if (!ctx_ || EVP_DigestInit_ex(ctx_, EVP_sha256(), nullptr) != 1) throw std::runtime_error("sha256 init failed");
  }
  ~Sha256Ctx() { EVP_MD_CTX_free(ctx_); }
  Sha256Ctx(const Sha256Ctx &) = delete;
  Sha256Ctx &operator=(const Sha256Ctx &) = delete;

  void update(const unsigned char *data, std::size_t size) {
    if (size == 0) return;
    if (EVP_DigestUpdate(ctx_, data, size) != 1) throw std::runtime_error("sha256 update failed");
  }

  std::string final() {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int len = 0;
    if (EVP_DigestFinal_ex(ctx_, digest, &len) != 1) throw std::runtime_error("sha256 final failed");
    return hex_digest(digest, len);
  }

 private:
  EVP_MD_CTX *ctx_ = nullptr;
};

}  // namespace

std::string sha256_bytes(const unsigned char *data, std::size_t size) {
  Sha256Ctx ctx;
  ctx.update(data, size);
  return ctx.final();
}

std::string sha256_string(const std::string &value) {
  return sha256_bytes(reinterpret_cast<const unsigned char *>(value.data()), value.size());
}

std::string sha256_file(const std::filesystem::path &path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open file for sha256: " + path.string());
  Sha256Ctx ctx;
  std::array<char, 65536> buffer{};
  while (in) {
    in.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    auto n = in.gcount();
    if (n > 0) ctx.update(reinterpret_cast<const unsigned char *>(buffer.data()), static_cast<std::size_t>(n));
  }
  if (in.bad()) throw std::runtime_error("cannot read file for sha256: " + path.string());
  return ctx.final();
}

std::string document_id(const std::string &repo_root, const std::string &relative_path) {
  return sha256_string(repo_root + "::" + relative_path).substr(0, 16);
}

std::string chunk_id(const std::string &repo_root, const std::string &relative_path, int line_start, int line_end, const std::string &content_hash) {
  const auto doc = document_id(repo_root, relative_path);
  return sha256_string(doc + ":" + std::to_string(line_start) + ":" + std::to_string(line_end) + ":" + content_hash).substr(0, 16);
}

}  // namespace dominion_native

