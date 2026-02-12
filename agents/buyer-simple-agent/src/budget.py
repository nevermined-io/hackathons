"""In-memory daily spending tracker for the data buying agent."""

import threading
from datetime import datetime, timezone


class Budget:
    """Thread-safe daily spending tracker with per-request limits."""

    def __init__(self, max_daily: int = 0, max_per_request: int = 0):
        """Initialize budget tracker.

        Args:
            max_daily: Maximum credits per day (0 = unlimited).
            max_per_request: Maximum credits per single request (0 = unlimited).
        """
        self._lock = threading.Lock()
        self._max_daily = max_daily
        self._max_per_request = max_per_request
        self._daily_spend = 0
        self._total_spend = 0
        self._purchase_count = 0
        self._current_day = datetime.now(timezone.utc).date()
        self._purchases: list[dict] = []

    def _reset_if_new_day(self):
        """Reset daily counter if the day has changed."""
        today = datetime.now(timezone.utc).date()
        if today != self._current_day:
            self._daily_spend = 0
            self._current_day = today

    def can_spend(self, credits: int) -> tuple[bool, str]:
        """Check if a purchase of the given credits is allowed.

        Returns:
            Tuple of (allowed, reason).
        """
        with self._lock:
            self._reset_if_new_day()

            if self._max_per_request > 0 and credits > self._max_per_request:
                return False, (
                    f"Request costs {credits} credits but per-request limit "
                    f"is {self._max_per_request}"
                )

            if self._max_daily > 0 and (self._daily_spend + credits) > self._max_daily:
                remaining = self._max_daily - self._daily_spend
                return False, (
                    f"Request costs {credits} credits but only {remaining} "
                    f"remaining in daily budget ({self._max_daily})"
                )

            return True, "OK"

    def record_purchase(self, credits: int, seller_url: str, query: str):
        """Record a completed purchase."""
        with self._lock:
            self._reset_if_new_day()
            self._daily_spend += credits
            self._total_spend += credits
            self._purchase_count += 1
            self._purchases.append({
                "credits": credits,
                "seller": seller_url,
                "query": query[:100],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def get_status(self) -> dict:
        """Return current budget snapshot."""
        with self._lock:
            self._reset_if_new_day()
            daily_remaining = (
                self._max_daily - self._daily_spend
                if self._max_daily > 0
                else "unlimited"
            )
            return {
                "daily_limit": self._max_daily or "unlimited",
                "daily_spent": self._daily_spend,
                "daily_remaining": daily_remaining,
                "per_request_limit": self._max_per_request or "unlimited",
                "total_spent": self._total_spend,
                "total_purchases": self._purchase_count,
                "recent_purchases": self._purchases[-5:],
            }
