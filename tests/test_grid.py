from collections import Counter
import hashlib
import json
from dataclasses import asdict

from injeval.grid import Cell, assign_items, enumerate_cells, run_order


def test_assign_items_uses_every_task_injection_pair_equally():
    items = assign_items(Cell("llama3.1:8b", "top", "imperative", 1), 24)
    pairs = Counter((t, i) for t, i, _ in items)
    assert len(pairs) == 12 and set(pairs.values()) == {2}


def test_assign_items_is_deterministic():
    c = Cell("llama3.1:8b", "top", "imperative", 1)
    assert assign_items(c, 24) == assign_items(c, 24)


def test_enumerate_cells_main_arm_has_36_cells():
    assert len(enumerate_cells("main")) == 36
    models = [c.model for c in enumerate_cells("main")]
    assert models == sorted(models, key=lambda m: m != "llama3.1:8b")


def test_each_model_block_is_bracketed_by_a_clean_baseline():
    order = run_order(["main", "baseline"], 24)
    assert len(order) == 960
    assert len({r.run_id for r in order}) == 960
    assert [r.model for r in order] == sorted([r.model for r in order], key=lambda m: m != "llama3.1:8b")
    for model in ("llama3.1:8b", "qwen3:8b"):
        block = [r for r in order if r.model == model]
        assert block[0].arm == block[-1].arm == "baseline"
    assert all(r.injection_id == "" for r in order if r.arm == "baseline")


def test_run_id_is_hash_of_full_identity():
    r = run_order(["main"], 1)[0]
    identity = [r.arm, asdict(r.cell), r.task_id, r.injection_id, r.seed]
    assert r.run_id == hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert run_order(["main"], 24)[0].run_id == r.run_id
