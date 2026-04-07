def strict_unit_interval(score: float) -> float:
    """Clamp scores into the open interval (0, 1) for evaluator compatibility."""
    bounded = max(0.0, min(1.0, score))
    if bounded <= 0.0:
        return 0.001
    if bounded >= 1.0:
        return 0.999
    return round(bounded, 3)

