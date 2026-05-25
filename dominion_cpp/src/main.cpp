#include "dominion/pipeline.hpp"
#include "dominion/config.hpp"
#include <iostream>
#include <csignal>
#include <atomic>

std::atomic<bool> running{true};

void signal_handler(int) {
    running = false;
    std::cout << "\nShutdown signal received..." << std::endl;
}

int main(int argc, char** argv) {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    try {
        std::cout << "Dominion Data Pipeline (C++) v2.0.0" << std::endl;
        std::cout << "====================================" << std::endl;

        // Load config
        auto config = dominion::Config::from_env();
        std::cout << "Loaded config from environment" << std::endl;
        std::cout << "Database: " << config.duckdb_path << std::endl;
        std::cout << "RAGD URL: " << config.ragd_url << std::endl;
        std::cout << std::endl;

        // Create pipeline
        dominion::Pipeline pipeline(config);

        // Set phase callback
        pipeline.set_phase_callback([](dominion::PipelinePhase phase, const std::string& msg) {
            // Callback for external monitoring (e.g., TUI)
        });

        // Run pipeline
        std::cout << "Starting pipeline..." << std::endl;
        pipeline.run();

        const auto& run = pipeline.last_run();
        std::cout << "\nPipeline completed successfully" << std::endl;
        std::cout << "Run ID: " << run.run_id << std::endl;
        std::cout << "Sources fetched: " << run.sources_fetched << std::endl;
        std::cout << "Features computed: " << run.features_computed << std::endl;

        if (!run.errors.empty()) {
            std::cout << "\nErrors encountered:" << std::endl;
            for (const auto& err : run.errors) {
                std::cout << "  - " << err << std::endl;
            }
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR: " << e.what() << std::endl;
        return 1;
    }
}
