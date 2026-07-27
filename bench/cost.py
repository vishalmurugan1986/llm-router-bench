"""Turn token counts into a $/ticket figure using router.candidates pricing."""

from __future__ import annotations

from router.candidates import get_candidate


def ticket_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    profile = get_candidate(model)
    return (
        (input_tokens / 1000) * profile.cost_per_1k_input
        + (output_tokens / 1000) * profile.cost_per_1k_output
    )


def mean_cost_per_ticket(costs: list[float]) -> float:
    if not costs:
        return 0.0
    return sum(costs) / len(costs)
