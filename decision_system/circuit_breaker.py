"""Simple circuit breaker — max hops counter (not full OPEN/HALF_OPEN state machine)"""
class CircuitBreaker:
    def __init__(self, max_hops: int = 5):
        self.max_hops = max_hops
        self._hop_count = 0

    def record_hop(self) -> None:
        self._hop_count += 1

    def check(self) -> bool:
        """Returns True if circuit should trip (hop limit reached)"""
        return self._hop_count >= self.max_hops

    def get_error(self) -> dict:
        return {
            "error": "circuit_open",
            "message": f"超过最大调用次数({self.max_hops}次)，熔断触发",
            "hops": self._hop_count
        }

    def reset(self) -> None:
        self._hop_count = 0
