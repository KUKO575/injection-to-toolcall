from dataclasses import replace

from injeval.agent import run_once
from injeval.client import Action
from injeval.grid import run_order
from injeval.record import RunRecord
from injeval.runner import pending_run_ids, run_study
from test_agent import FakeClient


def test_selected_pilot_schedule_and_resume(tmp_path):
    from injeval.grid import Cell
    from injeval.runner import study_order

    cells = [Cell('llama3.1:8b', 'top', 'imperative', 1),
             Cell('llama3.1:8b', 'bottom', 'prose', 5)]
    order = study_order(['pilot', 'baseline'], 12, cells)
    pilot = [r for r in order if r.arm == 'pilot']
    assert len(pilot) == 24
    assert all(sum(r.cell == cell for r in pilot) == 12 for cell in cells)
    baseline = [r for r in order if r.arm == 'baseline']
    assert baseline and all(r.model == 'llama3.1:8b' and not r.injection_id for r in baseline)
    assert order[0].arm == order[-1].arm == 'baseline'
    log = tmp_path / 'pilot.jsonl'
    record = replace(run_once(FakeClient([Action('final', text='a')]), 'c', 't', 's'),
                     run_id=pilot[0].run_id)
    log.write_text(record.to_json() + '\n', encoding='utf-8')
    assert pending_run_ids(log, ['pilot', 'baseline'], 12, cells) == {
        r.run_id for r in order} - {record.run_id}


def test_resume_skips_run_ids_already_in_the_log(tmp_path):
    log = tmp_path / "runs.jsonl"
    order = run_order(["main"], 24)
    record = replace(run_once(FakeClient([Action("final", text="a")]), "c", "t", "s"), run_id=order[4].run_id)
    log.write_text(record.to_json() + "\n", encoding="utf-8")
    assert pending_run_ids(log, ["main"], 24) == {r.run_id for r in order} - {record.run_id}


def test_run_study_clears_and_copies_hits_and_resumes(tmp_path, monkeypatch):
    import injeval.runner as runner
    listeners = []
    class Listener:
        def __init__(self, **kw):
            self.hits = [{"query": "stale"}]
            self.clears = 0
            self.stopped = False
            listeners.append(self)
        def start(self): pass
        def stop(self): self.stopped = True
        def clear(self):
            self.clears += 1
            self.hits.clear()
    monkeypatch.setattr(runner, "RecordingListener", Listener)
    order = run_order(["main"], 1)[:2]
    monkeypatch.setattr(runner, "run_order", lambda arms, n: order)
    monkeypatch.setattr(runner, "build_context", lambda *args: "context")
    monkeypatch.setattr(runner, "load_tasks", lambda: [{"id": "t1", "prompt": "task"}])
    monkeypatch.setattr(runner, "ModelClient", lambda **kw: FakeClient([]))
    def execute(*args):
        assert all(not l.hits for l in listeners)
        for l in listeners:
            l.hits.append({"query": "fresh"})
        return run_once(FakeClient([Action("unparseable")]), "c", "t", "s")
    monkeypatch.setattr(runner, "run_once", execute)
    log = tmp_path / "runs.jsonl"
    run_study(log, ["main"], 1)
    records = [RunRecord.from_json(s) for s in log.read_text().splitlines()]
    assert len(records) == 2 and all(r.parse_failed for r in records)
    assert all(r.benign_hits == r.attacker_hits == [{"query": "fresh"}] for r in records)
    assert all(l.clears == 2 and l.stopped for l in listeners)
    run_study(log, ["main"], 1)
    assert len(log.read_text().splitlines()) == 2
