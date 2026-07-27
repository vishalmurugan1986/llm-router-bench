"""Run every candidate model against the full golden set, capturing quality,
cost, and latency for each. Output: one timestamped JSON file per model under
results/matrix_runs/, plus an aggregated scorecard used by router/policy.py.

Usage:
    python -m bench.run_matrix --provider openai --judge-mode mock
    python -m bench.run_matrix --offline  # CI-safe mode using MockProvider
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from agent.schemas import Ticket

from bench.cost import ticket_cost_usd, mean_cost_per_ticket
from bench.latency import p50, p95
from bench.score import build_judge, score_one
from router.candidates import CANDIDATES
from router.llm import NIMProvider
from router.schemas import ModelScorecard
from agent.schemas import Decision

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "golden")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "matrix_runs")


def load_golden(limit: int | None = None) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.jsonl"))):
        suite = os.path.basename(path).replace(".jsonl", "")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    rec["_suite"] = suite
                    rows.append(rec)
                    if limit and len(rows) >= limit:
                        return rows
    return rows


class DummyProvider:
    def decide(self, ticket: Ticket) -> Decision:
        return Decision(
            category="refund_request",
            action="auto_resolve",
            tool_calls=[{"name": "order_lookup", "args": {"order_id": "123"}}, {"name": "refund_policy", "args": {}}],
            draft_reply="I can help with your refund.",
        )


def run_for_model(model_name: str, judge_mode: str, limit: int | None = None, offline: bool = False) -> ModelScorecard:
    if offline:
        provider = DummyProvider()
    else:
        provider = NIMProvider(model=model_name)
    judge = build_judge(use_mock=(judge_mode == "mock"))
    rows = load_golden(limit=limit)

    latencies, costs, results = [], [], []
    missed_escalations = 0
    injection_total, injection_refused = 0, 0

    for rec in rows:
        ticket = Ticket(**rec["ticket"])
        run = provider.decide(ticket)          # calls NIM (or mock), parses -> Decision + real usage
        
        # MockProvider returns a raw Decision, NIMProvider returns a UsageResult
        if offline:
            decision = run
            latencies.append(150.0)
            input_tokens = 100
            output_tokens = 50
        else:
            decision = run.decision
            latencies.append(run.latency_ms)
            input_tokens = run.input_tokens
            output_tokens = run.output_tokens

        costs.append(
            ticket_cost_usd(
                model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )

        scored = score_one(rec, decision, judge, use_mock_judge=(judge_mode == "mock"))
        results.append(scored)

        if rec["expected"].get("action") == "escalate_human" and decision.action != "escalate_human":
            missed_escalations += 1
        if scored["adversarial"]:
            injection_total += 1
            if scored["judge"].get("refused_injection") == "pass":
                injection_refused += 1

    n = len(results)
    action_passed = sum(1 for r in results if r["deterministic"]["action_match"] and r["deterministic"]["tool_ok"] and r["judge"]["passed"])
    category_passed = sum(1 for r in results if r["deterministic"]["category_match"])

    card = ModelScorecard(
        model=model_name,
        tier=next(c.tier for c in CANDIDATES if c.name == model_name),
        action_accuracy=action_passed / n if n else 0.0,
        category_accuracy=category_passed / n if n else 0.0,
        injection_refusal_rate=(injection_refused / injection_total) if injection_total else 1.0,
        missed_escalations=missed_escalations,
        cost_per_ticket_usd=mean_cost_per_ticket(costs),
        p50_latency_ms=p50(latencies),
        p95_latency_ms=p95(latencies),
        meets_quality_bar=False,  # filled in by router.policy at report time
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe_model_name = model_name.replace("/", "_")
    out_path = os.path.join(RESULTS_DIR, f"{ts}_{safe_model_name}.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"card": card.model_dump(), "results": results}, f, indent=2)

    return card


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--models", nargs="*", default=[c.name for c in CANDIDATES])
    parser.add_argument("--limit", type=int, default=None, help="Max tickets to run per model")
    parser.add_argument("--offline", action="store_true", help="Use MockProvider for agents (for CI)")
    args = parser.parse_args()

    from router.policy import meets_bar
    cards = [run_for_model(m, args.judge_mode, args.limit, args.offline) for m in args.models]
    for c in cards:
        status = "✅" if meets_bar(c) else "❌"
        print(f"{c.model:35s} action_acc={c.action_accuracy:.2f}  cat_acc={c.category_accuracy:.2f}  $/ticket={c.cost_per_ticket_usd:.4f}  p95={c.p95_latency_ms:.0f}ms  {status}")


if __name__ == "__main__":
    main()
