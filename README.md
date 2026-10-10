# Injection-to-Tool-Call Measurement Harness

A local experiment measuring text-level and tool-call outcomes separately for
indirect prompt injection. The writer agent originates from
[agent-sandbox](https://github.com/cherrypickersGuild/agent-sandbox).

The current implementation provides the frozen `RunRecord` schema, JSON
serialization, and validation of the five study arms.

Requires Python 3.11 or later. Install development dependencies and run the tests:

```powershell
python -m pip install -e ".[dev]"
pytest tests/test_record.py -v
```

The experiment design and implementation plan are in
`docs/superpowers/specs/2026-10-10-injection-to-toolcall-design.md` and
`docs/superpowers/plans/2026-10-10-injection-toolcall-harness-plan.md`.
