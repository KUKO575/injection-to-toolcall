import pytest

from injeval.record import RunRecord


def test_record_roundtrips_through_json():
    r = RunRecord(run_id="r1", timestamp="2026-10-11T00:00:00Z", model="llama3.1:8b",
                  position="top", framing="imperative", dilution=1, task_id="t1",
                  injection_id="i1", seed=0, temperature=0.7, arm="main",
                  prompt="p", final_answer="a", tool_calls=[], benign_hits=[],
                  attacker_hits=[], steps_used=2, wall_clock_s=1.5, parse_failed=False, max_steps=8)
    assert RunRecord.from_json(r.to_json()) == r


def test_record_rejects_unknown_arm():
    with pytest.raises(ValueError):
        RunRecord(run_id="r1", timestamp="2026-10-11T00:00:00Z", model="llama3.1:8b",
                  position="top", framing="imperative", dilution=1, task_id="t1",
                  injection_id="i1", seed=0, temperature=0.7, arm="whatever",
                  prompt="p", final_answer="a", tool_calls=[], benign_hits=[],
                  attacker_hits=[], steps_used=2, wall_clock_s=1.5, parse_failed=False, max_steps=8)
