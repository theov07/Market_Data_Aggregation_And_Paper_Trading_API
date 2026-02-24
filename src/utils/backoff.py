"""
Exponential backoff utilities for robust reconnection logic
"""
import random
from typing import Callable


def compute_backoff(
    attempt: int,
    base: float = 0.5,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    rand_fn: Callable[[float, float], float] = None
) -> float:
    """
    Compute exponential backoff delay with jitter.
    
    Args:
        attempt: Current reconnection attempt (0-based)
        base: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Jitter proportion (0..1) applied to delay
        rand_fn: Random function for jitter (default: random.uniform)
    
    Returns:
        Delay in seconds
    """
    if rand_fn is None:
        rand_fn = random.uniform
    
    # Exponential backoff: base * 2^attempt
    delay = base * (2 ** attempt)
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter: delay * (1 ± jitter)
    if jitter > 0:
        jitter_range = delay * jitter
        delay = delay + rand_fn(-jitter_range, jitter_range)
    
    # Ensure non-negative
    return max(0.0, delay)
