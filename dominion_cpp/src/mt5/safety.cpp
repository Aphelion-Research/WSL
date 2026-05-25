#include <iostream>
#include <stdexcept>

namespace dominion {

// Read-only guard for MT5 API
// Prevents trading functions from being called

constexpr const char* BLOCKED_MSG = "DOMDATA READ-ONLY GUARD: trading function blocked.";

void blocked_order_send() {
    throw std::runtime_error(BLOCKED_MSG);
}

void blocked_order_check() {
    throw std::runtime_error(BLOCKED_MSG);
}

// TODO: Replace MT5 API function pointers with blocked versions
// This requires linking against MT5 API and patching function table

void apply_read_only_guard() {
    // TODO: Patch MT5 API:
    // mt5_api.order_send = blocked_order_send;
    // mt5_api.order_check = blocked_order_check;
    std::cout << "MT5 read-only guard applied\n";
}

} // namespace dominion
