#pragma once

#include "dominion/config.hpp"
#include "dominion/types.hpp"

#include <string>
#include <variant>
#include <vector>

namespace dominion {

struct SourceResult {
    std::string source_name;
    std::vector<Bar> bars;
    std::vector<MacroData> macro;
    std::vector<COTData> cot;
    double latency_ms = 0.0;
    std::string error;
    bool success = true;
};

class DataSource {
public:
    virtual ~DataSource() = default;
    virtual SourceResult fetch() = 0;
    virtual std::string name() const = 0;
};

class YahooSource : public DataSource {
public:
    explicit YahooSource(const Config& config);
    SourceResult fetch() override;
    std::string name() const override { return "yahoo"; }
private:
    Config config_;
};

class FREDSource : public DataSource {
public:
    explicit FREDSource(const Config& config);
    SourceResult fetch() override;
    std::string name() const override { return "fred"; }
private:
    Config config_;
};

class AlphaVantageSource : public DataSource {
public:
    explicit AlphaVantageSource(const Config& config);
    SourceResult fetch() override;
    std::string name() const override { return "alphavantage"; }
private:
    Config config_;
    std::filesystem::path cache_path_;
};

class COTSource : public DataSource {
public:
    explicit COTSource(const Config& config);
    SourceResult fetch() override;
    std::string name() const override { return "cot"; }
private:
    Config config_;
};

class MT5Source : public DataSource {
public:
    explicit MT5Source(const Config& config);
    SourceResult fetch() override;
    std::string name() const override { return "mt5"; }
private:
    Config config_;
};

} // namespace dominion
