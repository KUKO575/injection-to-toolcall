from injeval.agent import run_once
from injeval.client import Action


class FakeClient:
    model = "llama3.1:8b"
    temperature = 0.7
    interface = "json"

    def __init__(self, actions):
        self.actions = iter(actions)
        self.messages = []

    def act(self, messages):
        self.messages.append(list(messages))
        return next(self.actions)


def test_agent_stops_at_max_steps(monkeypatch):
    monkeypatch.setattr("injeval.agent.fetch_reference", lambda **kw: "ok")
    a = Action("tool", "fetch_reference", {"url": "http://127.0.0.1:8731/ref"})
    assert run_once(FakeClient([a] * 10), "c", "t", "s", max_steps=10).steps_used == 6


def test_agent_continues_after_attacker_fetch_so_task_ok_is_measurable(monkeypatch):
    monkeypatch.setattr("injeval.agent.fetch_reference", lambda **kw: "")
    monkeypatch.setattr("injeval.agent.save_note", lambda **kw: "note.md")
    client = FakeClient([
        Action("tool", "fetch_reference", {"url": "http://127.0.0.1:8732/ref"}),
        Action("tool", "save_note", {"title": "t", "body": "b"}),
        Action("final", text="done"),
    ])
    r = run_once(client, "c", "t", "s")
    assert [tc["name"] for tc in r.tool_calls] == ["fetch_reference", "save_note"]
    assert r.final_answer == "done" and r.steps_used == 3
    assert client.messages[1][-1]["content"] == ""


def test_unparseable_action_sets_parse_failed_and_does_not_crash():
    r = run_once(FakeClient([Action("unparseable", raw="garbage")]), "c", "t", "s")
    assert r.parse_failed and r.steps_used == 1


def test_tool_error_is_an_observation(monkeypatch):
    def fail(**kw):
        raise ValueError("bad title")
    monkeypatch.setattr("injeval.agent.save_note", fail)
    client = FakeClient([Action("tool", "save_note", {"title": "t", "body": "b"}),
                         Action("final", text="done")])
    assert run_once(client, "c", "t", "s").final_answer == "done"
    assert "bad title" in client.messages[1][-1]["content"]
