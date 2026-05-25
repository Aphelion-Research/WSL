#pragma once

#include "dominion/types.hpp"
#include <vector>
#include <string>

#ifdef DOMINION_HAS_IGRAPH
#include <igraph/igraph.h>
#endif

namespace dominion::network {

// Correlation network
struct CorrelationNetwork {
    std::vector<std::string> nodes;
    std::vector<std::vector<double>> adjacency;  // Correlation matrix
    std::vector<double> centrality;              // Centrality scores
    double density;
};

#ifdef DOMINION_HAS_IGRAPH
CorrelationNetwork compute_correlation_network(
    const std::vector<PriceVec>& series,
    const std::vector<std::string>& names,
    double threshold = 0.5,
    int window = 252
);
#endif

// Minimum spanning tree
std::vector<std::pair<int,int>> compute_mst(const std::vector<PriceVec>& series);

// Betweenness centrality
PriceVec compute_betweenness_centrality(const PriceVec& target_series, const std::vector<PriceVec>& all_series, int window = 252);

// Community detection (Louvain)
std::vector<int> detect_communities(const std::vector<PriceVec>& series, int window = 252);

} // namespace dominion::network
