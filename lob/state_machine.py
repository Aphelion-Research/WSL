"""LOB state machine implementation."""
import json
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import uuid


class LimitOrderBook:
    """Limit order book with 10-level depth per side."""

    def __init__(self, depth: int = 10):
        """Initialize LOB.

        Args:
            depth: Number of price levels to maintain per side
        """
        self.depth = depth
        # Each side: {price: size}
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}

    def update_bid(self, price: float, size: float) -> None:
        """Update bid side.

        Args:
            price: Bid price
            size: Bid size (0 = remove)
        """
        if size > 0:
            self.bids[price] = size
        elif price in self.bids:
            del self.bids[price]

        # Keep only top N levels
        if len(self.bids) > self.depth:
            sorted_bids = sorted(self.bids.keys(), reverse=True)
            self.bids = {p: self.bids[p] for p in sorted_bids[:self.depth]}

    def update_ask(self, price: float, size: float) -> None:
        """Update ask side.

        Args:
            price: Ask price
            size: Ask size (0 = remove)
        """
        if size > 0:
            self.asks[price] = size
        elif price in self.asks:
            del self.asks[price]

        # Keep only top N levels
        if len(self.asks) > self.depth:
            sorted_asks = sorted(self.asks.keys())
            self.asks = {p: self.asks[p] for p in sorted_asks[:self.depth]}

    def get_best_bid(self) -> Optional[float]:
        """Get best bid price."""
        return max(self.bids.keys()) if self.bids else None

    def get_best_ask(self) -> Optional[float]:
        """Get best ask price."""
        return min(self.asks.keys()) if self.asks else None

    def get_mid(self) -> Optional[float]:
        """Get mid price."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2.0
        return None

    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid is not None and best_ask is not None:
            return best_ask - best_bid
        return None

    def get_depth_weighted_mid(self) -> Optional[float]:
        """Get depth-weighted mid price.

        Formula: (bid * ask_size + ask * bid_size) / (bid_size + ask_size)
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid is None or best_ask is None:
            return None

        bid_size = self.bids.get(best_bid, 0)
        ask_size = self.asks.get(best_ask, 0)

        if bid_size + ask_size == 0:
            return self.get_mid()

        return (best_bid * ask_size + best_ask * bid_size) / (bid_size + ask_size)

    def get_depth_imbalance(self) -> float:
        """Get depth imbalance: (bid_depth - ask_depth) / (bid_depth + ask_depth).

        Returns:
            Imbalance in [-1, 1]: -1 = all asks, +1 = all bids, 0 = balanced
        """
        bid_depth = sum(self.bids.values())
        ask_depth = sum(self.asks.values())

        if bid_depth + ask_depth == 0:
            return 0.0

        return (bid_depth - ask_depth) / (bid_depth + ask_depth)

    def get_total_bid_depth(self) -> float:
        """Get total bid size."""
        return sum(self.bids.values())

    def get_total_ask_depth(self) -> float:
        """Get total ask size."""
        return sum(self.asks.values())

    def snapshot(self) -> Dict:
        """Get current book state as dict."""
        return {
            'snapshot_id': str(uuid.uuid4())[:8],
            'bids': sorted([(p, s) for p, s in self.bids.items()], reverse=True),
            'asks': sorted([(p, s) for p, s in self.asks.items()]),
            'mid_price': self.get_mid(),
            'spread': self.get_spread(),
            'total_bid_depth': self.get_total_bid_depth(),
            'total_ask_depth': self.get_total_ask_depth(),
            'depth_imbalance': self.get_depth_imbalance(),
            'depth_weighted_mid': self.get_depth_weighted_mid()
        }
