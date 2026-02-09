"""In-memory usage analytics for the data selling agent."""

import threading
from datetime import datetime, timezone


class Analytics:
    """Thread-safe in-memory usage tracker."""

    def __init__(self):
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_credits = 0
        self._subscribers: set[str] = set()
        self._requests_by_tier: dict[str, int] = {}
        self._started_at = datetime.now(timezone.utc).isoformat()

    def record_request(self, tier: str, credits: int, subscriber_id: str = "anonymous"):
        """Record a completed request."""
        with self._lock:
            self._total_requests += 1
            self._total_credits += credits
            self._subscribers.add(subscriber_id)
            self._requests_by_tier[tier] = self._requests_by_tier.get(tier, 0) + 1

    def get_stats(self) -> dict:
        """Return current analytics snapshot."""
        with self._lock:
            avg = (
                self._total_credits / self._total_requests
                if self._total_requests > 0
                else 0
            )
            return {
                "totalRequests": self._total_requests,
                "totalCreditsEarned": self._total_credits,
                "uniqueSubscribers": len(self._subscribers),
                "averageCreditsPerRequest": round(avg, 2),
                "requestsByTier": dict(self._requests_by_tier),
                "startedAt": self._started_at,
            }


# Singleton instance
analytics = Analytics()
