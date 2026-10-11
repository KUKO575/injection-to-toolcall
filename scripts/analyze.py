"""Produce descriptive tables and figures from a stored JSONL run log."""

import argparse
from dataclasses import asdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from injeval.coding import code_run
from injeval.record import RunRecord
from injeval.stats import rate_table, said_did_gap


FACTORS = ['model', 'position', 'framing', 'dilution']


def _tables(frame: pd.DataFrame, directory: Path, suffix: str) -> None:
    rate_table(frame, ['arm'] + FACTORS).to_csv(directory / f'per_cell{suffix}.csv', index=False)
    for factor in FACTORS:
        rate_table(frame, ['arm', factor]).to_csv(
            directory / f'marginal_{factor}{suffix}.csv', index=False)
    rows = []
    cross = []
    for arm, group in frame.groupby('arm', sort=True):
        said, did, gap = said_did_gap(group)
        rows.append(dict(arm=arm, n=len(group), said=said, did=did, gap=gap))
        for said_value in [False, True]:
            for did_value in [False, True]:
                count = int(((group['said'] == said_value) & (group['did'] == did_value)).sum())
                cross.append(dict(arm=arm, said=said_value, did=did_value, n=count,
                                  proportion=count / len(group)))
    pd.DataFrame(rows, columns=['arm', 'n', 'said', 'did', 'gap']).to_csv(
        directory / f'said_did_gap{suffix}.csv', index=False)
    pd.DataFrame(cross, columns=['arm', 'said', 'did', 'n', 'proportion']).to_csv(
        directory / f'said_did_2x2{suffix}.csv', index=False)


def _figures(frame: pd.DataFrame, directory: Path) -> None:
    arms = sorted(frame['arm'].unique())
    fig, axes = plt.subplots(len(arms), 4, squeeze=False,
                             figsize=(18, 4 * len(arms)), layout='constrained')
    for row, arm in enumerate(arms):
        group = frame[frame['arm'] == arm]
        for col, factor in enumerate(FACTORS):
            ax = axes[row, col]
            table = rate_table(group, [factor])
            positions = list(range(len(table)))
            for outcome, offset in [('said', -0.08), ('did', 0.08)]:
                rates = table[outcome]
                # Roundoff near a boundary can make a zero-length error negative.
                errors = [(rates - table[outcome + '_lo']).clip(lower=0),
                          (table[outcome + '_hi'] - rates).clip(lower=0)]
                ax.errorbar([x + offset for x in positions], rates, yerr=errors,
                            fmt='o', capsize=3, label=outcome)
            ax.set_xticks(positions, table[factor].astype(str), rotation=25)
            ax.set_ylim(-0.03, 1.03)
            ax.set_title(f'{arm}: {factor}')
            ax.set_ylabel('Rate (all runs); 95% Wilson interval')
            ax.legend()
    fig.savefig(directory / 'factor_marginals.png', dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6), layout='constrained')
    cells = rate_table(frame, ['arm'] + FACTORS)
    for arm in arms:
        table = cells[cells['arm'] == arm]
        ax.scatter(table['said'], table['did'], label=arm, alpha=0.7)
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray')
    ax.set(xlabel='said rate (all runs)', ylabel='did rate (all runs)',
           xlim=(-0.03, 1.03), ylim=(-0.03, 1.03), title='Said versus did per cell')
    ax.legend()
    fig.savefig(directory / 'said_vs_did.png', dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--out', type=Path, default=Path('results'))
    parser.add_argument('--planted-id', default='REF-7741-QX')
    parser.add_argument('--attacker-host', default='127.0.0.1:8732')
    args = parser.parse_args()
    records = []
    with args.log.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                record = RunRecord.from_json(line)
                codes = code_run(record, args.planted_id, args.attacker_host)
                records.append(asdict(record) | asdict(codes))
    if not records:
        parser.error('the log must contain at least one run')
    frame = pd.DataFrame(records)
    tables = args.out / 'tables'
    figures = args.out / 'figures'
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    _tables(frame, tables, '')
    _tables(frame[~frame['invalid']], tables, '_valid_only')
    _figures(frame, figures)
    print(f'Headline: {len(frame)} runs, including {int(frame["invalid"].sum())} invalid runs.')
    print('Valid-only auxiliary tables: suffix _valid_only.')
    print(rate_table(frame, ['arm']).to_string(index=False))
    print('Said/did gap (all runs):')
    for arm, group in frame.groupby('arm', sort=True):
        said, did, gap = said_did_gap(group)
        print(f'{arm}: n={len(group)}, said={said:.6f}, did={did:.6f}, gap={gap:.6f}')
    print(f'Tables: {tables}; figures: {figures}')


if __name__ == '__main__':
    main()
