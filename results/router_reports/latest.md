# Model Router Report

| Model | Tier | Action Acc | Category Acc | Injection Refusal | Missed Escalations | $/ticket | p95 (ms) | Meets Bar |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-20b | small | 90.91% | 68.18% | 100.00% | 1 | $0.0001 | 10712 | ❌ |
| openai/gpt-oss-120b | mid | 90.91% | 86.36% | 93.33% | 0 | $0.0002 | 152488 | ❌ |
| nvidia/nemotron-3-ultra-550b-a55b | frontier | 100.00% | 90.91% | 100.00% | 0 | $0.0025 | 40434 | ✅ |

**Router verdict:** route to `nvidia/nemotron-3-ultra-550b-a55b` (cheapest model clearing the quality bar).