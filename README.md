# Model Router Bench

Eval-driven model router. Runs the same agent task across multiple candidate
models, scores each with an external eval harness, and picks the **cheapest
model that clears a quality bar** — with automatic fallback to a stronger
model on low-confidence tickets.

This repo is standalone: it does not read from or write into the
`agent-eval-harness` repo. It consumes it as a normal pip dependency.

## Dependency on P1

This repo imports `agent.schemas`, `evals.deterministic`, and `evals.judge`
from the harness. It installs cleanly via:

```
agent-eval-harness @ git+https://github.com/vishalmurugan1986/agent-eval-harness@v0.1.0
```

The harness is packaged and tagged. No manual setup required beyond
`pip install -e ".[dev]"`.

## Results

**Bench run** (agent: three NIM candidates, judge: live, n=22 golden rows)*:

*\*Metrics verified against a live Nemotron judge via NVIDIA NIM on 2026-07-25.*

| Model | Action accuracy | Injection refusal | Missed escalations | $/ticket | Selected |
|---|---|---|---|---|---|
| openai/gpt-oss-20b | 90.9% | 100% | 1 | $0.0001 | |
| openai/gpt-oss-120b | 90.9% | 93.3% | 0 | $0.0002 | |
| nvidia/nemotron-3-ultra-550b-a55b | 100% | 100% | 0 | $0.0025 | ✓ sole viable |

**Key findings:**

The naive blended accuracy metric passed a model that failed injection
refusal at **93.3%** (required: 100%). After splitting the metric into
`action_accuracy` (deployment-gating) and `category_accuracy`
(analytics-only), the router correctly disqualified it — a failure a
single accuracy score would have hidden.

Both cheaper candidates were disqualified — gpt-oss-120b on injection refusal, gpt-oss-20b on missed escalations. The router correctly prevented deploying either. The cost saving here is preventing a safety failure, not reducing inference cost.

## Regressions caught in development

| What | Before | After | How caught |
|---|---|---|---|
| Blended accuracy metric conflated safety-critical routing failures with cosmetic label errors | Single `accuracy` score hid injection failures | Split: `action_accuracy` (deployment-gating) vs `category_accuracy` (analytics-only) | Metric analysis during scoring design |
| Model passed overall accuracy bar but failed injection refusal at 93.3% vs required 100% | Would have been selected as cheapest viable | Correctly disqualified; next model selected | Non-negotiable injection gate enforced independently of accuracy |

## Models & endpoint

All three candidates run through **NVIDIA NIM** (build.nvidia.com) — one
base URL, one API key, for `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and
`nvidia/nemotron-3-ultra-550b-a55b`. Get a key at build.nvidia.com and set
it as `NVIDIA_API_KEY`.

**Cost caveat:** NIM's hosted API is currently free (rate-limited, ~40
req/min as of writing). `router/candidates.py` prices each model at
published market rates (OpenRouter/Artificial Analysis medians) so the
$/ticket numbers model what these calls would cost on a paid provider —
they are not a real NIM invoice. Re-check those figures periodically;
open-weight model pricing moves fast.

Because of the rate limit, `bench/run_matrix.py` runs sequentially and can
take a while on a large golden set — worth adding a `--limit N` flag or
some concurrency-with-backoff if the golden set grows.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
cp .env.example .env   # add your NVIDIA_API_KEY
pip install -e ".[dev]"
```

## Run the bench

```bash
python -m bench.run_matrix --judge-mode mock          # fast, offline, CI-safe
python -m bench.run_matrix --judge-mode live           # real judge model
python -m dashboard.report                              # generate the report
```

## What it measures per model

- **Accuracy** — deterministic + judge pass rate on the golden set
- **Injection refusal rate** — must be 100%, non-negotiable
- **Missed escalations** — must be 0, non-negotiable
- **$/ticket** — mean cost across the golden set
- **p50 / p95 latency**

## Router logic

`router/policy.py` picks the lowest-cost model among those that clear the
quality bar. `router/fallback.py` provides a per-ticket safety valve:
low-confidence outputs (empty replies, failed deterministic checks) get
re-routed to a stronger model rather than shipped as-is.

## Roadmap

- [x] Package P1 (`agent-eval-harness`) so this installs cleanly
- [x] Wire real token usage from provider `resp.usage` instead of the placeholder in `run_matrix.py`
- [ ] Add a live-traffic sampling mode instead of golden-set-only

## What's Next

- **Dynamic router recalibration**: Automatically update fallback thresholds and routing policies based on continuous online evaluation feedback from the production drift monitor (see P3). When P3 detects a quality regression on the deployed model, P2 re-runs the bench and promotes the next viable candidate.
- **Multi-turn evaluation**: Extend the harness to handle multi-turn conversational agents, preserving context and grading cumulative task success instead of single-turn static inputs.
