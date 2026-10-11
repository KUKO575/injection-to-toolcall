"""Run two fixed pilot cells (12 runs each) and their clean baselines."""

import argparse
from pathlib import Path

from injeval.gate import pilot_gate
from injeval.grid import Cell
from injeval.record import RunRecord
from injeval.runner import run_study, study_order

PILOT_CELLS = [
    Cell('llama3.1:8b', 'top', 'imperative', 1),
    Cell('llama3.1:8b', 'bottom', 'prose', 5),
]
N = 12


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('results/pilot.jsonl'))
    args = parser.parse_args()
    arms = ['pilot', 'baseline']
    run_study(args.out, arms, N, cells=PILOT_CELLS)
    planned_ids = {run.run_id for run in study_order(arms, N, PILOT_CELLS)}
    with args.out.open(encoding='utf-8') as stream:
        records = [RunRecord.from_json(line) for line in stream if line.strip()]
    ok, why = pilot_gate(record for record in records if record.run_id in planned_ids)
    print(f"Pilot gate: {'PASS' if ok else 'FAIL'}; reason: {why}")


if __name__ == '__main__':
    main()
