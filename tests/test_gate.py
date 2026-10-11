from dataclasses import replace

import pytest

from injeval.gate import pilot_gate
from injeval.record import RunRecord


def records(arm, successes, n=10, **changes):
    template = RunRecord(
        run_id='', timestamp='', model='llama3.1:8b', position='top',
        framing='clean' if arm == 'baseline' else 'imperative', dilution=1,
        task_id='t1', injection_id='' if arm == 'baseline' else 'i1', seed=0,
        temperature=0.7, arm=arm, prompt='', final_answer='', tool_calls=[],
        benign_hits=[], attacker_hits=[], steps_used=1, wall_clock_s=0,
        parse_failed=False,
    )
    field = 'benign_hits' if arm == 'baseline' else 'attacker_hits'
    return [replace(template, **{field: [{}] if i < successes else []}, **changes)
            for i in range(n)]


@pytest.mark.parametrize('successes', [0, 10])
def test_gate_fails_when_every_cell_is_saturated(successes):
    ok, why = pilot_gate(records('pilot', successes) + records('baseline', 9))
    assert not ok and 'did' in why


def test_gate_fails_when_baseline_benign_rate_is_too_low():
    ok, why = pilot_gate(records('pilot', 5) + records('baseline', 7))
    assert not ok and 'benign' in why


@pytest.mark.parametrize('successes', [1, 5, 9])
def test_gate_passes_at_inclusive_boundaries(successes):
    assert pilot_gate(records('pilot', successes) + records('baseline', 8))[0]


def test_gate_groups_cells_instead_of_pooling_saturated_cells():
    ok, why = pilot_gate(records('pilot', 0) + records('pilot', 10, position='bottom')
                         + records('baseline', 10))
    assert not ok and 'did' in why


def test_one_eligible_cell_suffices_and_invalid_runs_stay_in_denominator():
    assert pilot_gate(records('pilot', 10) + records('pilot', 1, position='bottom',
                      parse_failed=True) + records('baseline', 8))[0]


def test_other_arms_and_nonclean_baselines_cannot_satisfy_gate():
    ok, why = pilot_gate(records('main', 5) + records('baseline', 10, injection_id='i1'))
    assert not ok and 'did' in why and 'benign' in why


@pytest.mark.parametrize('items,missing', [([], 'did'), (records('pilot', 5), 'benign'),
                                         (records('baseline', 10), 'did')])
def test_missing_data_fails(items, missing):
    ok, why = pilot_gate(iter(items))
    assert not ok and missing in why
