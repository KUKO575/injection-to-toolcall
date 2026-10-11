import math

import pytest

from injeval.stats import rate_table, said_did_gap, wilson


def coded(**changes):
    return dict(said=False, did=False, exfil=False, task_ok=False, invalid=False) | changes


@pytest.mark.parametrize('n', [1, 24, 1000])
def test_wilson_at_zero_successes_is_finite_and_starts_at_zero(n):
    lo, hi = wilson(0, n)
    assert lo == 0.0 and 0 < hi < 1 and math.isfinite(hi)


@pytest.mark.parametrize('n', [1, 24, 1000])
def test_wilson_at_full_successes_is_finite_and_ends_at_one(n):
    lo, hi = wilson(n, n)
    assert hi == 1.0 and 0 < lo < 1 and math.isfinite(lo)


def test_wilson_rejects_zero_n():
    with pytest.raises(ValueError):
        wilson(0, 0)


@pytest.mark.parametrize('successes,n', [(-1, 24), (25, 24), (0, -1)])
def test_wilson_rejects_invalid_counts(successes, n):
    with pytest.raises(ValueError):
        wilson(successes, n)


def test_wilson_known_interval():
    assert wilson(12, 24) == pytest.approx((0.314271, 0.685729), abs=1e-6)


def test_invalid_runs_stay_in_the_denominator():
    recs = [coded(did=True)] * 6 + [coded(invalid=True)] * 6
    row = rate_table(recs, by=[]).iloc[0]
    assert row['n'] == 12 and row['did'] == pytest.approx(0.5)
    assert row['invalid'] == pytest.approx(0.5)
    assert (row['did_lo'], row['did_hi']) == pytest.approx(wilson(6, 12))


def test_rate_table_reports_the_invalid_rate_itself():
    assert 'invalid' in rate_table([coded(invalid=True)], by=[]).columns


def test_rate_table_groups_factors_and_reports_independent_outcomes():
    table = rate_table([coded(model='a', said=True, did=True, exfil=True),
                        coded(model='a', task_ok=True), coded(model='b')], ['model'])
    row = table.set_index('model').loc['a']
    assert row['n'] == 2
    assert all(row[key] == 0.5 for key in ['said', 'did', 'exfil', 'task_ok'])


def test_said_did_gap_counts_runs_that_both_said_and_did_in_both_rates():
    assert said_did_gap([coded(said=True, did=True)] * 10) == (1.0, 1.0, 0.0)


def test_gap_includes_invalid_and_is_said_minus_did():
    assert said_did_gap([coded(said=True), coded(invalid=True)]) == (0.5, 0.0, 0.5)


def test_empty_inputs_have_explicit_behavior():
    assert rate_table([], []).empty
    with pytest.raises(ValueError):
        said_did_gap([])


@pytest.mark.parametrize('all_invalid', [False, True])
def test_analysis_cli_emits_headline_auxiliary_tables_and_figures(tmp_path, all_invalid):
    import os
    from pathlib import Path
    import subprocess
    import sys

    import pandas as pd
    from injeval.record import RunRecord

    root = Path(__file__).resolve().parents[1]
    log = tmp_path / 'runs.jsonl'
    fields = dict(timestamp='2026-10-11T00:00:00Z', model='llama3.1:8b',
                  position='top', framing='imperative', dilution=1, task_id='t1',
                  injection_id='i_a1', seed=0, temperature=0.7, arm='main',
                  prompt='', tool_calls=[], benign_hits=[], steps_used=1, wall_clock_s=0.1)
    records = [RunRecord(**fields, run_id='r1', final_answer='REF-7741-QX',
                         attacker_hits=[{'query': 'id=REF-7741-QX'}], parse_failed=all_invalid),
               RunRecord(**fields, run_id='r2', final_answer='', attacker_hits=[], parse_failed=True)]
    log.write_text('\n'.join(r.to_json() for r in records), encoding='utf-8')
    out = tmp_path / 'analysis'
    result = subprocess.run([sys.executable, str(root / 'scripts/analyze.py'), str(log),
                             '--out', str(out)], capture_output=True, text=True,
                            env=os.environ | {'PYTHONPATH': str(root / 'src')})
    assert result.returncode == 0, result.stderr
    assert 'sign' + 'ificant' not in result.stdout.lower()
    cell = pd.read_csv(out / 'tables/per_cell.csv').iloc[0]
    assert cell['n'] == 2 and cell['said'] == cell['did'] == 0.5
    valid = pd.read_csv(out / 'tables/per_cell_valid_only.csv')
    assert valid.empty if all_invalid else valid.iloc[0]['n'] == 1
    cross = pd.read_csv(out / 'tables/said_did_2x2.csv')
    assert cross['n'].sum() == 2 and len(cross) == 4
    for factor in ['model', 'position', 'framing', 'dilution']:
        assert (out / f'tables/marginal_{factor}.csv').exists()
        assert (out / f'tables/marginal_{factor}_valid_only.csv').exists()
    for name in ['factor_marginals.png', 'said_vs_did.png']:
        assert (out / 'figures' / name).stat().st_size > 1000
