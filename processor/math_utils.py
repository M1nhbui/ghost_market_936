from collections import deque
import time


class SlidingWindow:
    """
    Memory-efficient sliding window using deque with a time-based expiry.
    Automatically evicts data points older than `window_seconds`.
    All operations are O(1) amortized.
    """

    def __init__(self, window_seconds: int = 300):
        """
        Args:
            window_seconds: How far back to look. Default = 5 minutes (300s).
        """
        self.window_seconds = window_seconds
        self._data: deque[tuple[float, float]] = deque()  # (timestamp, value)

    def add(self, value: float, timestamp: float | None = None) -> None:
        """
        Append a new data point and evict expired entries.

        Args:
            value: The numeric value to store (price or vibe score).
            timestamp: Unix timestamp. Defaults to now if not provided.
        """
        if timestamp is None:
            timestamp = time.time()

        self._data.append((timestamp, value))
        self._evict_expired(timestamp)

    def _evict_expired(self, now: float) -> None:
        """Remove entries older than window_seconds from the left."""
        cutoff = now - self.window_seconds
        while self._data and self._data[0][0] < cutoff:
            self._data.popleft()

    def average(self) -> float | None:
        """
        Compute rolling mean of current window.
        Returns None if window is empty.
        """
        if not self._data:
            return None
        return sum(v for _, v in self._data) / len(self._data)

    def count(self) -> int:
        """Message velocity: number of data points in current window."""
        return len(self._data)

    def latest(self) -> float | None:
        """Most recent value in the window. Returns None if empty."""
        if not self._data:
            return None
        return self._data[-1][1]

    def __repr__(self) -> str:
        return (
            f"SlidingWindow(window={self.window_seconds}s, "
            f"count={self.count()}, avg={self.average():.4f})"
            if self._data else
            f"SlidingWindow(window={self.window_seconds}s, empty)"
        )


# --- Decoupling Metrics ---

def delta_price(p_current: float, p_avg: float) -> float | None:
    """
    Relative price move from rolling average.
    ΔP = (P_current - P_avg) / P_avg

    Returns None if p_avg is 0 (avoid division by zero).
    """
    if p_avg == 0:
        return None
    return (p_current - p_avg) / p_avg


def delta_vibe(v_current: float, v_avg: float) -> float:
    """
    Absolute vibe shift from rolling average.
    ΔV = V_current - V_avg
    """
    return v_current - v_avg


def hype_momentum(dv: float, n: int) -> float:
    """
    Volume-gated hype signal.
    M_hype = ΔV × N

    Args:
        dv: delta_vibe value
        n:  message velocity (count in window)
    """
    return dv * n


def check_alert(m_hype: float, dp: float) -> str | None:
    """
    Fire alert if hype is high but price hasn't moved yet.

    Conditions:
        M_hype > 100  → strong positive vibe with high message volume
        ΔP < 0.02     → price has NOT reacted yet (< 2% move)

    Returns:
        "IMMINENT_HYPE_PUMP" or None
    """
    if m_hype > 1 and dp < 0.02:
        return "IMMINENT_HYPE_PUMP"
    return None


# --- Run standalone to verify math ---
if __name__ == "__main__":
    print("=== SlidingWindow Test ===")
    window = SlidingWindow(window_seconds=10)

    for i, val in enumerate([0.1, 0.3, -0.2, 0.8, 0.5]):
        window.add(val, timestamp=time.time() + i)

    print(f"Count  : {window.count()}")
    print(f"Average: {window.average():.4f}")
    print(f"Latest : {window.latest()}")
    print(window)

    print("\n=== Decoupling Metrics Test ===")
    dp = delta_price(p_current=62500, p_avg=62000)
    dv = delta_vibe(v_current=0.8, v_avg=0.1)
    mh = hype_momentum(dv=dv, n=150)
    alert = check_alert(m_hype=mh, dp=dp)

    print(f"ΔP           : {dp:.4f}")
    print(f"ΔV           : {dv:.4f}")
    print(f"M_hype       : {mh:.2f}")
    print(f"Alert        : {alert}")