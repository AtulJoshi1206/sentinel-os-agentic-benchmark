def grader(trajectory):
    steps = len(trajectory)

    fixed = any(
        hasattr(a, "tool") and hasattr(a, "cmd") and
        a.tool == "terminal" and a.cmd == "update_config"
        for a in trajectory
    )

    if not fixed:
        return 0.0

    if steps <= 7:
        return 1.0
    elif steps <= 10:
        return 0.7
    else:
        return 0.3
