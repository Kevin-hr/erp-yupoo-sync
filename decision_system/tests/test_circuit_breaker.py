import pytest
from decision_system.circuit_breaker import CircuitBreaker

def test_max_hops_5():
    cb = CircuitBreaker(max_hops=5)
    for _ in range(5):
        cb.record_hop()
    assert cb.check() is True

def test_circuit_open_error():
    cb = CircuitBreaker(max_hops=5)
    for _ in range(5):
        cb.record_hop()
    err = cb.get_error()
    assert err["error"] == "circuit_open"
    assert "5" in err["message"]

