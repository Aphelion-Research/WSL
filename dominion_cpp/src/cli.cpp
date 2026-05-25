#include "dominion/pipeline.hpp"
#include "dominion/config.hpp"
#include "dominion/health.hpp"
#include "dominion/storage.hpp"

#include <iostream>
#include <string>
#include <vector>

void print_usage() {
    std::cout << "Dominion CLI - Data Pipeline Management\n";
    std::cout << "\nUsage: dominion_cli <command> [options]\n";
    std::cout << "\nCommands:\n";
    std::cout << "  run [--sources SOURCE,...]   Run pipeline (optionally filter sources)\n";
    std::cout << "  status                        Show source health status\n";
    std::cout << "  doctor                        Run comprehensive health check\n";
    std::cout << "  report                        Generate and display latest report\n";
    std::cout << "  features [--top N]            Show top N features by IC (default 20)\n";
    std::cout << "  backfill --days N             Backfill N days (NYI)\n";
    std::cout << "  version                       Show version\n";
    std::cout << "\nExamples:\n";
    std::cout << "  dominion_cli run\n";
    std::cout << "  dominion_cli run --sources yahoo,fred\n";
    std::cout << "  dominion_cli status\n";
    std::cout << "  dominion_cli features --top 50\n";
}

int cmd_run(const std::vector<std::string>& args) {
    auto config = dominion::Config::from_env();
    dominion::Pipeline pipeline(config);

    std::vector<std::string> sources;
    for (size_t i = 0; i < args.size(); ++i) {
        if (args[i] == "--sources" && i + 1 < args.size()) {
            // Parse comma-separated sources
            std::string sources_str = args[i + 1];
            size_t pos = 0;
            while ((pos = sources_str.find(',')) != std::string::npos) {
                sources.push_back(sources_str.substr(0, pos));
                sources_str.erase(0, pos + 1);
            }
            if (!sources_str.empty()) sources.push_back(sources_str);
        }
    }

    pipeline.run(sources);
    return 0;
}

int cmd_status(const std::vector<std::string>&) {
    auto config = dominion::Config::from_env();
    dominion::PipelineMonitor monitor(config.duckdb_path.string());
    auto staleness = monitor.check_staleness(config.staleness_hours);

    std::cout << "Source Health Status\n";
    std::cout << "====================\n\n";

    for (const auto& [source, status] : staleness) {
        std::cout << source << ":\n";
        std::cout << "  Status: " << (status.is_stale ? "STALE" : "OK") << "\n";
        std::cout << "  Last fetch: " << status.age_seconds << "s ago\n";
        std::cout << "  Threshold: " << status.threshold_seconds << "s\n\n";
    }

    return 0;
}

int cmd_doctor(const std::vector<std::string>&) {
    auto config = dominion::Config::from_env();
    dominion::PipelineMonitor monitor(config.duckdb_path.string());
    auto summary = monitor.get_health_summary(config.staleness_hours);

    std::cout << "Pipeline Health Check\n";
    std::cout << "=====================\n\n";

    std::cout << "Staleness:\n";
    for (const auto& [source, status] : summary.staleness) {
        std::cout << "  " << source << ": ";
        std::cout << (status.is_stale ? "STALE" : "OK") << "\n";
    }

    std::cout << "\nGaps: " << summary.gaps.size() << " detected\n";

    std::cout << "\nRecent anomalies: " << summary.recent_anomalies.size() << "\n";
    for (const auto& a : summary.recent_anomalies) {
        std::cout << "  " << a.type << " (" << a.severity << "): " << a.description << "\n";
    }

    std::cout << "\nGold-DXY correlation: ";
    std::cout << (summary.gold_dxy_inverted ? "INVERTED" : "normal");
    std::cout << " (" << summary.gold_dxy_correlation << ")\n";

    std::cout << "\nOverall: " << (summary.overall_healthy ? "HEALTHY" : "UNHEALTHY") << "\n";

    return 0;
}

int cmd_features(const std::vector<std::string>& args) {
    int top_n = 20;
    for (size_t i = 0; i < args.size(); ++i) {
        if (args[i] == "--top" && i + 1 < args.size()) {
            top_n = std::stoi(args[i + 1]);
        }
    }

    auto config = dominion::Config::from_env();
    dominion::Storage storage(config.duckdb_path.string());
    auto importance = storage.get_feature_importance(top_n);

    std::cout << "Top " << top_n << " Features by IC\n";
    std::cout << "==============================\n\n";

    // Sort by absolute IC
    std::vector<std::pair<std::string, double>> sorted(importance.begin(), importance.end());
    std::sort(sorted.begin(), sorted.end(),
              [](const auto& a, const auto& b) { return std::abs(a.second) > std::abs(b.second); });

    for (size_t i = 0; i < sorted.size() && i < static_cast<size_t>(top_n); ++i) {
        std::cout << i + 1 << ". " << sorted[i].first << ": " << sorted[i].second << "\n";
    }

    return 0;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage();
        return 1;
    }

    std::string command = argv[1];
    std::vector<std::string> args(argv + 2, argv + argc);

    try {
        if (command == "run") {
            return cmd_run(args);
        } else if (command == "status") {
            return cmd_status(args);
        } else if (command == "doctor") {
            return cmd_doctor(args);
        } else if (command == "features") {
            return cmd_features(args);
        } else if (command == "version") {
            std::cout << "Dominion v2.0.0\n";
            return 0;
        } else {
            std::cerr << "Unknown command: " << command << "\n\n";
            print_usage();
            return 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << "\n";
        return 1;
    }
}
