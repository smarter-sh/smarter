import random
import time


def mock_test_provider_verification(success_probability: float = 1.00) -> bool:
    """Mock function to simulate provider verification."""

    duration = min(max(1, int(random.expovariate(1 / 30))), 180)
    time.sleep(duration)

    return random.random() < success_probability
