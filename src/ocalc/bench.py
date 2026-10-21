"""Time a function across a size grid and record peak Python allocations."""

def geometric_sizes(min_n: int, max_n: int, measures: int) -> list[int]:
    """Evenly spaced sizes on a log scale, including both ends."""
    if measures < 1:
        raise ValueError("measures must be at least 1")
    if min_n > max_n:
        raise ValueError("min_n cannot be greater than max_n")
    if measures == 1 or min_n == max_n:
        return [int(max_n)]
    ratio = (max_n / min_n) ** (1 / (measures - 1))
    raw = [int(round(min_n * ratio**i)) for i in range(measures)]
    raw[0] = int(min_n)
    raw[-1] = int(max_n)
    sizes: list[int] = []
    for size in raw:
        size = max(int(min_n), size)
        if not sizes or size > sizes[-1]:
            sizes.append(size)
    if sizes[-1] != int(max_n):
        sizes.append(int(max_n))
    return sizes
