from signalloop_api.rate_limit import InMemoryRateLimiter


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False
