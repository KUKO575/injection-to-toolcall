# Action interface reliability check

Date: 2026-10-11
20 single-turn prompts per model per interface.

| model | interface | n | unparseable | rate | expected call rate |
|---|---|---|---|---|---|
| llama3.1:8b | native | 20 | 0 | 0.00% | 100.00% |
| llama3.1:8b | json   | 20 | 0 | 0.00% | 100.00% |
| qwen3:8b    | native | 20 | 0 | 0.00% | 100.00% |
| qwen3:8b    | json   | 20 | 0 | 0.00% | 100.00% |

## Limitation

The check used single-turn prompts with one tool and an explicit URL. It is
much easier than the study condition (6-step loop, k=5 retrieval context, two
tools, a competing injected instruction), so these rates do not estimate the
parse failure rate of the main run. The check establishes only that neither
interface is broken. The real per-model invalid rate is measured in the pilot
and reported in the main run.

## Decision: json

The two interfaces tied, so the choice was made on a design ground rather than
on the numbers. Native tool calling is rendered by each model's own chat
template, so llama3.1 and qwen3 would receive structurally different
instructions. The study treats model as a factor, and the design requires the
action interface to be identical across models so the two are not confounded.
The JSON interface gives both models byte-identical instructions and the same
parser, and its failures surface as `invalid` rather than silently.