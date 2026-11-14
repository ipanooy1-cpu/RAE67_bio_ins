"""Lab06/07 completed baseline FSM; proposed course model, no learning.
Safety and output limits remain in the original course engine.
"""
def transition(current_state: str, event: str) -> str | None:
    # Safety events override all other transitions, including afraid guard.
    if event == "fault":
        return "normal"
    if event == "near":
        return "afraid"
    if event == "clear":
        return "normal"
    # Do not leave danger state on a delayed positive interaction.
    if current_state == "afraid":
        return None
    if event == "touch":
        return "happy"
    if event in ("button", "approach"):
        return "interested"
    if event == "timeout" and current_state in ("interested", "happy"):
        return "normal"
    if event == "idle" and current_state == "normal":
        return "sleepy"
    return None
