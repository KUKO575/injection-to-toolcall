"""Deterministic factor and item schedules, blocked by model."""

from dataclasses import asdict, dataclass
import hashlib
from itertools import product
import json

MODELS = ("llama3.1:8b", "qwen3:8b")
FRAMINGS = ("imperative", "system_notice", "prose")


@dataclass(frozen=True)
class Cell:
    model: str
    position: str
    framing: str
    dilution: int


@dataclass(frozen=True)
class PlannedRun:
    arm: str
    cell: Cell
    task_id: str
    injection_id: str
    seed: int

    @property
    def model(self) -> str:
        return self.cell.model

    @property
    def run_id(self) -> str:
        identity = [self.arm, asdict(self.cell), self.task_id, self.injection_id, self.seed]
        return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def enumerate_cells(arm: str) -> list[Cell]:
    if arm == "baseline":
        return [Cell(m, "top", "clean", d) for m, d in product(MODELS, (1, 5))]
    if arm not in {"main", "pilot", "defense", "defense_control"}:
        raise ValueError(f"Unknown arm: {arm}")
    return [Cell(*values) for values in product(MODELS, ("top", "middle", "bottom"), FRAMINGS, (1, 5))]


def assign_items(cell: Cell, n: int) -> list[tuple[str, str, int]]:
    if n < 0:
        raise ValueError("n must be nonnegative")
    injections = ("",) if cell.framing == "clean" else tuple(
        f"i{FRAMINGS.index(cell.framing) * 3 + j}" for j in range(1, 4))
    pairs = list(product(("t1", "t2", "t3", "t4"), injections))
    return [(*pairs[k % len(pairs)], k // len(pairs)) for k in range(n)]


def run_order(arms: list[str], n: int) -> list[PlannedRun]:
    if n < 1:
        raise ValueError("n must be positive")
    cells = {arm: enumerate_cells(arm) for arm in dict.fromkeys(arms)}
    order = []
    for model in MODELS:
        baseline = [PlannedRun("baseline", c, *item)
                    for c in cells.get("baseline", []) if c.model == model
                    for item in assign_items(c, n)]
        split = (len(baseline) + 1) // 2
        order.extend(baseline[:split])
        for arm, arm_cells in cells.items():
            if arm != "baseline":
                order.extend(PlannedRun(arm, c, *item) for c in arm_cells if c.model == model
                             for item in assign_items(c, n))
        order.extend(baseline[split:])
    return order
