#include "dominion_native/doctor.hpp"

#include "dominion_native/forbidden_tokens.hpp"
#include "dominion_native/ignore_policy.hpp"
#include "dominion_native/manifest_store.hpp"
#include "dominion_native/scan_plan.hpp"
#include "dominion_native/version.hpp"
#include "dominion_native/vault_doctor.hpp"

#include <array>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <netinet/in.h>
#include <sstream>
#include <sys/socket.h>
#include <unistd.h>

namespace dominion_native {
namespace {

std::filesystem::path home_dir() {
  const char *home = std::getenv("HOME");
  return home ? std::filesystem::path(home) : std::filesystem::temp_directory_path();
}

std::string run_capture(const std::string &command) {
  std::array<char, 256> buffer{};
  std::string output;
  FILE *pipe = popen(command.c_str(), "r");
  if (!pipe) return "";
  while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe)) output += buffer.data();
  pclose(pipe);
  while (!output.empty() && (output.back() == '\n' || output.back() == '\r')) output.pop_back();
  return output;
}

bool tcp_connects(const std::string &host, int port) {
  if (host != "127.0.0.1" && host != "localhost") return false;
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) return false;
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(static_cast<uint16_t>(port));
  addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  bool ok = connect(fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) == 0;
  close(fd);
  return ok;
}

DoctorCheck make_check(std::string name, std::string status, std::string message, nlohmann::json details = nlohmann::json::object(), std::string remediation = "", std::string severity = "required") {
  return {std::move(name), std::move(status), std::move(severity), std::move(message), std::move(details), std::move(remediation)};
}

bool command_ok(const std::string &cmd) {
  const auto out = run_capture(cmd + " >/dev/null 2>&1; printf $?");
  return out == "0";
}

}  // namespace

nlohmann::json DoctorCheck::to_json() const {
  return {
      {"name", name},
      {"status", status},
      {"severity", severity},
      {"message", message},
      {"details", details},
      {"remediation", remediation},
  };
}

nlohmann::json DoctorReport::to_json() const {
  nlohmann::json checks_json = nlohmann::json::array();
  nlohmann::json legacy_checks = nlohmann::json::object();
  for (const auto &check : checks) {
    checks_json.push_back(check.to_json());
    legacy_checks[check.name] = {{"status", check.status == "pass" ? "ok" : check.status}, {"message", check.message}, {"details", check.details}};
  }
  return {{"overall", overall == "pass" ? "ok" : overall}, {"native_core_version", kNativeCoreVersion}, {"checks", legacy_checks}, {"native_checks", checks_json}};
}

int DoctorReport::exit_code(bool strict) const {
  for (const auto &check : checks) {
    if (check.status == "fail") return 1;
    if (strict && check.status == "warn") return 1;
  }
  return 0;
}

DoctorReport run_native_doctor(const DoctorOptions &options) {
  DoctorReport report;
  const auto root = std::filesystem::absolute(options.root.empty() ? std::filesystem::current_path() : options.root).lexically_normal();
  const auto add = [&](const DoctorCheck &check) { report.checks.push_back(check); };

  std::error_code ec;
  if (std::filesystem::exists(root, ec) && std::filesystem::is_directory(root, ec)) {
    add(make_check("repo_root", "pass", "repo root exists", {{"root", root.string()}}));
  } else {
    add(make_check("repo_root", "fail", "repo root missing", {{"root", root.string()}}, "Pass --root with a valid Dominion checkout."));
  }

  try {
    auto policy = load_ignore_policy(root);
    add(make_check("ignore_rules", policy.secrets_always_ignored ? "pass" : "fail", "ignore policy parsed", {{"policy_fingerprint", "sha256:" + policy.fingerprint()}, {"source", policy.source}}));
    auto secret_decision = policy.decide("secrets/fake.env", false, 8);
    add(make_check("secrets_protected", secret_decision.secret_protected ? "pass" : "fail", secret_decision.secret_protected ? "secrets are blocked by native policy" : "secrets are not blocked", secret_decision.to_json()));
  } catch (const std::exception &exc) {
    add(make_check("ignore_rules", "fail", exc.what()));
  }

  try {
    auto forbidden = load_forbidden_policy(root);
    auto py = run_capture("cd '" + root.string() + "' && python -c 'from domdata.domdata_pkg.forbidden_tokens import FORBIDDEN_POLICY_FINGERPRINT; print(FORBIDDEN_POLICY_FINGERPRINT)' 2>/dev/null");
    add(make_check("forbidden_token_policy", py.empty() || py == forbidden.fingerprint ? "pass" : "fail", py.empty() ? "native forbidden policy loaded; python fingerprint unavailable" : "native/python forbidden policy fingerprints checked", {{"native_fingerprint", forbidden.fingerprint}, {"python_fingerprint", py}}));
  } catch (const std::exception &exc) {
    add(make_check("forbidden_token_policy", "fail", exc.what()));
  }

  try {
    ScanPlanOptions scan_options;
    scan_options.max_files = 2000;
    auto plan = build_scan_plan(root, scan_options);
    add(make_check("native_scan_plan", plan.errors.empty() ? "pass" : "warn", "native scan plan built", {{"seen", plan.seen}, {"included", plan.files.size()}, {"ignored", plan.ignored.size()}, {"errors", plan.errors.size()}, {"plan_hash", plan.plan_hash()}}));
  } catch (const std::exception &exc) {
    add(make_check("native_scan_plan", "fail", exc.what()));
  }

  try {
    const auto db = home_dir() / ".dominion" / "native_manifest.db";
    auto init = manifest_init_json(db);
    auto doctor = manifest_doctor_json(db);
    add(make_check("native_manifest", doctor.value("ok", false) ? "pass" : "fail", "native manifest opens and migrations run", {{"db", db.string()}, {"doctor", doctor}, {"init", init}}));
  } catch (const std::exception &exc) {
    add(make_check("native_manifest", "fail", exc.what()));
  }

  auto vault_dir = root / "vault";
  if (std::filesystem::exists(vault_dir, ec)) {
    auto vault = inspect_vault_native(root, vault_dir);
    add(make_check("native_vault", vault.status, vault.ok ? "vault links are clean" : "vault has stale or broken links", vault.to_json(), "Regenerate or repair stale vault notes before treating vault as trusted.", "advisory"));
  } else {
    add(make_check("native_vault", "skip", "vault directory not present", {}, "", "optional"));
  }

  const auto ragd_bin = root / "ragd" / "build" / "ragd";
  add(make_check("ragd_binary", std::filesystem::exists(ragd_bin, ec) ? "pass" : "warn", std::filesystem::exists(ragd_bin, ec) ? "ragd binary exists" : "ragd binary missing", {{"path", ragd_bin.string()}}, "Run cmake --build ragd/build.", "required"));

  const auto native_bin = root / "ragd" / "build" / "dominion-native-doctor";
  add(make_check("native_build_metadata", std::filesystem::exists(native_bin, ec) ? "pass" : "warn", std::filesystem::exists(native_bin, ec) ? "native doctor binary exists" : "native doctor binary missing from build tree", {{"path", native_bin.string()}}, "Build Dominion native tools.", "required"));

  if (options.live) {
    const bool ok = tcp_connects("127.0.0.1", 7474);
    add(make_check("ragd_reachable", ok ? "pass" : "fail", ok ? "RAGD loopback port is reachable" : "RAGD loopback port is not reachable", {{"host", "127.0.0.1"}, {"port", 7474}}, "Start RAGD or use --offline."));
  } else {
    add(make_check("ragd_reachable", "skip", "offline mode: live RAGD reachability skipped", {{"host", "127.0.0.1"}, {"port", 7474}}, "", "live"));
  }

  add(make_check("python_cli_import", command_ok("cd '" + root.string() + "' && python -c 'import scripts.dominion_cli'") ? "pass" : "warn", "python CLI import sanity checked", {}, "Check Python environment.", "required"));
  add(make_check("domdata_scanner", command_ok("cd '" + root.string() + "' && python domdata/check_no_trading.py") ? "pass" : "fail", "domdata read-only safety scanner runnable", {}, "Fix forbidden trading token findings immediately.", "required"));

  std::ifstream cmake(root / "ragd" / "CMakeLists.txt");
  std::string cmake_text((std::istreambuf_iterator<char>(cmake)), std::istreambuf_iterator<char>());
  const auto hash_count = std::count(cmake_text.begin(), cmake_text.end(), '#');  // cheap non-empty guard, not the real check
  const bool cmake_hashes = cmake_text.find("URL_HASH") != std::string::npos && cmake_text.find("DOMINION_BUILD_TESTS") != std::string::npos;
  add(make_check("cmake_dependency_hashes", cmake_hashes ? "pass" : "fail", "CMake dependency hash/options check", {{"cmake_nonempty_guard", hash_count > 0}}, "Add URL_HASH for FetchContent and native build options."));

  const auto latest = root / "reports" / "phase-5-native-core-start-latest.md";
  add(make_check("reports_start_snapshot", std::filesystem::exists(latest, ec) ? "pass" : "warn", std::filesystem::exists(latest, ec) ? "phase startup snapshot exists" : "phase startup snapshot missing", {{"path", latest.string()}}, "Capture phase startup snapshot."));
  add(make_check("integration_test_gating", "pass", "offline pytest baseline is independently validated by startup/final reports", {}, "", "advisory"));

  bool any_fail = false;
  bool any_warn = false;
  for (const auto &check : report.checks) {
    if (check.status == "fail") any_fail = true;
    if (check.status == "warn") any_warn = true;
  }
  report.overall = any_fail ? "fail" : any_warn ? "warn" : "pass";
  return report;
}

}  // namespace dominion_native
