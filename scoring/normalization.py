"""
Peer Group Normalization Module (Phase E).

Implements category-relative percentile/rank-based normalization for Fund Quality
dimensions.

Enforces:
- Directionality awareness (higher is better vs lower is better).
- Strict bounds in [0.0, 100.0].
- Deterministic handling of ties and small peer groups.
"""

from typing import List, Dict, Any, Optional, Tuple


class PeerGroupNormalizer:
    """Normalizes raw metric values relative to a category peer group."""

    def normalize_dimension(
        self,
        target_value: Optional[float],
        peer_values: List[float],
        higher_is_better: bool = True
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Normalizes a target metric value against peer values.
        Returns (peer_percentile, normalized_score) in [0.0, 100.0].
        """
        if target_value is None:
            return None, None

        # Filter valid numeric peer values
        valid_peers = [v for v in peer_values if v is not None]
        if target_value not in valid_peers:
            valid_peers.append(target_value)

        valid_peers.sort()
        n = len(valid_peers)

        if n < 2:
            # Fallback for single peer: neutral 50.0 percentile
            return 50.0, 50.0

        # Calculate rank with tie-handling (fractional ranking)
        rank_sum = 0.0
        count = 0
        for idx, val in enumerate(valid_peers):
            if val == target_value:
                rank_sum += (idx + 1)
                count += 1

        avg_rank = rank_sum / count if count > 0 else 1.0

        # Midpoint percentile formula: (rank - 0.5) / n * 100
        raw_percentile = round(((avg_rank - 0.5) / n) * 100.0, 2)

        # Apply directionality
        if not higher_is_better:
            normalized_score = round(100.0 - raw_percentile, 2)
        else:
            normalized_score = raw_percentile

        # Clamp strictly between 0.0 and 100.0
        normalized_score = max(0.0, min(100.0, normalized_score))
        return raw_percentile, normalized_score
