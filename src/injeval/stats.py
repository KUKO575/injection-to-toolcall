"""Descriptive rates and Wilson score intervals over independently coded runs."""

from dataclasses import asdict, is_dataclass
from math import isfinite, sqrt
from operator import index

import pandas as pd


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    try:
        successes, n = index(successes), index(n)
    except TypeError as exc:
        raise ValueError('counts must be integers') from exc
    if n <= 0 or successes < 0 or successes > n:
        raise ValueError('counts must satisfy n > 0 and 0 <= successes <= n')
    if not isfinite(z) or z <= 0:
        raise ValueError('z must be finite and positive')
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (0.0 if successes == 0 else max(0.0, center - half),
            1.0 if successes == n else min(1.0, center + half))


def _frame(records) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        return records.copy()
    return pd.DataFrame([asdict(r) if is_dataclass(r) else dict(r) for r in records])


def rate_table(records, by: list[str]) -> pd.DataFrame:
    """Include every supplied run in the denominator, including invalid runs."""
    frame = _frame(records)
    columns = by + ['n', 'said', 'said_lo', 'said_hi', 'did', 'did_lo',
                    'did_hi', 'exfil', 'task_ok', 'invalid']
    if frame.empty:
        return pd.DataFrame(columns=columns)
    groups = frame.groupby(by, dropna=False, sort=True) if by else [((), frame)]
    rows = []
    for key, group in groups:
        keys = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, keys))
        n = len(group)
        row['n'] = n
        for outcome in ['said', 'did', 'exfil', 'task_ok', 'invalid']:
            successes = int(group[outcome].sum())
            row[outcome] = successes / n
            if outcome in {'said', 'did'}:
                row[outcome + '_lo'], row[outcome + '_hi'] = wilson(successes, n)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def said_did_gap(records) -> tuple[float, float, float]:
    frame = _frame(records)
    if frame.empty:
        raise ValueError('at least one run is required')
    said = float(frame['said'].sum() / len(frame))
    did = float(frame['did'].sum() / len(frame))
    return said, did, said - did
