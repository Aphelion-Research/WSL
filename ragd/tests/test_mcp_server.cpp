#include "ragd/mcp_server.h"
#include <cassert>
#include <filesystem>
int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-mcp.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::RagEngine r(s);
  assert(ragd::mcp_manifest_json().find("ragd_query") != std::string::npos);
  auto res = ragd::mcp_handle_json(R"({"jsonrpc":"2.0","id":1,"method":"tools/list"})", s, r);
  assert(res.find("ragd_query") != std::string::npos);
  return 0;
}
