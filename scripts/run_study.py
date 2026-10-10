"""Run the local study; Task 6's corpus must be installed first."""

import argparse
from pathlib import Path

from injeval.runner import run_study


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", default=["main", "baseline"],
                        choices=["main", "baseline", "pilot", "defense", "defense_control"])
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--out", type=Path, default=Path("results/runs.jsonl"))
    args = parser.parse_args()
    run_study(args.out, args.arms, args.n)


if __name__ == "__main__":
    main()
