"""Turn matrix_runs/*.json into a single markdown report: quality vs cost vs
latency, with the router's verdict on which model it would pick.
"""

from __future__ import annotations

import glob
import json
import os

from router.policy import choose_cheapest_viable, meets_bar
from router.schemas import ModelScorecard

MATRIX_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "matrix_runs")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "router_reports")


def load_latest_cards() -> list[ModelScorecard]:
    latest_by_model: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(MATRIX_DIR, "*.json"))):
        model = os.path.basename(path).split("_", 1)[1].removesuffix(".json")
        latest_by_model[model] = path  # sorted filenames -> last write wins

    cards = []
    for path in latest_by_model.values():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        card = ModelScorecard(**data["card"])
        card.meets_quality_bar = meets_bar(card)
        cards.append(card)
    return cards


def render(cards: list[ModelScorecard]) -> str:
    winner = choose_cheapest_viable(cards)
    lines = [
        "# Model Router Report",
        "",
        "| Model | Tier | Action Acc | Category Acc | Injection Refusal | Missed Escalations | $/ticket | p95 (ms) | Meets Bar |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in sorted(cards, key=lambda c: c.cost_per_ticket_usd):
        mark = "✅" if c.meets_quality_bar else "❌"
        lines.append(
            f"| {c.model} | {c.tier} | {c.action_accuracy:.2%} | {c.category_accuracy:.2%} | {c.injection_refusal_rate:.2%} | "
            f"{c.missed_escalations} | ${c.cost_per_ticket_usd:.4f} | {c.p95_latency_ms:.0f} | {mark} |"
        )
    lines.append("")
    if winner:
        lines.append(f"**Router verdict:** route to `{winner.model}` (cheapest model clearing the quality bar).")
    else:
        lines.append("**Router verdict:** no candidate clears the quality bar -- escalate everything to frontier.")
    return "\n".join(lines)


def main():
    cards = load_latest_cards()
    report = render(cards)
    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, "latest.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
