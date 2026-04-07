def grader(trajectory):
    read_logs = False
    fixed = False

    for action in trajectory:
        if hasattr(action, "tool") and hasattr(action, "cmd"):
            if action.tool == "terminal" and action.cmd == "cat":
                read_logs = True
            if action.tool == "terminal" and action.cmd == "update_config":
                fixed = True

    if read_logs and fixed:
        return 1.0
    elif fixed:
        return 0.4
    return 0.0
