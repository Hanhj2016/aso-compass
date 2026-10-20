from app.services.rate_limit import SlidingWindowLimiter


def test_sliding_window_limiter_releases_expired_requests() -> None:
    limiter = SlidingWindowLimiter(window_seconds=60)

    assert limiter.allow("client", 2, now=0)
    assert limiter.allow("client", 2, now=10)
    assert not limiter.allow("client", 2, now=20)
    assert limiter.allow("client", 2, now=61)
    assert limiter.allow("other-client", 2, now=20)
