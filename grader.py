def compute_res(history):
    """Calculates Recovery Efficiency Score (RES)"""
    log_checks = sum(1 for h in history if "cat" in h)
    retries = sum(1 for h in history if "fetch" in h)

    if retries == 0:
        return 0.0

    # Logic: Checking logs before/during retries shows intelligence
    return min(1.0, log_checks / retries)


def grade_trajectory(state):
    """Final Score Calculation for the Environment"""
    history = state.get("history", [])
    res = compute_res(history)
    
    score = 0.0

    # Condition 1: System Recovery (Success)
    if state.get("api_version") == state.get("correct_api") and not state.get("broken"):
        score += 0.5

    # Condition 2: Step Efficiency (Penalty for dragging)
    steps = state.get("step", 1)
    score += max(0, 0.3 - (steps * 0.01))

    # Condition 3: Recovery Intelligence (The RES Factor)
    score += res * 0.2

    return round(min(1.0, score), 3)
