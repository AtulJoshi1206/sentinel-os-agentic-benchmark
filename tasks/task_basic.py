def grader(trajectory):
    for action in trajectory:
        if hasattr(action, "tool") and hasattr(action, "cmd"):
            if action.tool == "terminal" and action.cmd == "update_config":
                return 1.0
    return 0.0
