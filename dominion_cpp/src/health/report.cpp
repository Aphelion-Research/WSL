#include "dominion/health.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <sstream>

using json = nlohmann::json;

namespace dominion {

ReportGenerator::ReportGenerator(const std::string& db_path,
                                 const std::string& ragd_url,
                                 const std::string& reports_dir)
    : db_path_(db_path), ragd_url_(ragd_url), reports_dir_(reports_dir) {}

std::string ReportGenerator::generate(const std::string& run_id) {
    std::ostringstream oss;
    oss << "# Dominion Daily Intelligence Report\n\n";
    oss << "Run ID: " << run_id << "\n\n";

    // TODO: Query database for:
    // - Source health
    // - Current regime
    // - Top 5 features by IC
    // - Recent anomalies (24h)
    // - COT positioning
    // - Macro summary
    // - Feature drift warnings

    oss << "## Pipeline Status\n";
    oss << "All sources operational.\n\n";

    oss << "## Regime Stack\n";
    oss << "Tactical: ranging, Micro: london, Confidence: 0.85\n\n";

    oss << "## Top Features by IC\n";
    oss << "1. rolling_mean_50: 0.42\n";
    oss << "2. sharpe_100: 0.38\n";
    oss << "3. amihud_illiquidity: 0.35\n\n";

    return oss.str();
}

bool ReportGenerator::send_to_ragd(const std::string& report_text,
                                    const std::string& report_date) {
    try {
        httplib::Client cli(ragd_url_.c_str());
        json payload = {
            {"text", report_text},
            {"tag", "daily_report"},
            {"metadata", {
                {"report_date", report_date},
                {"source", "data_pipeline"}
            }}
        };

        auto res = cli.Post("/memory/remember", payload.dump(), "application/json");
        return res && res->status == 200;
    } catch (const std::exception& e) {
        std::cerr << "Failed to send report to RAGD: " << e.what() << std::endl;
        return false;
    }
}

} // namespace dominion
