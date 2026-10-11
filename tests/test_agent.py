import pytest

from injeval.agent import FORMAT_GUIDANCE, run_once
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
    r = run_once(FakeClient([a] * 10), "c", "t", "s", max_steps=10)
    assert r.steps_used == 8 and r.max_steps == 8


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
    assert r.max_steps == 8
    assert client.messages[1][-1]["content"] == ""


def test_unparseable_action_sets_parse_failed_and_does_not_crash():
    client = FakeClient([Action("unparseable", raw="garbage")] * 3)
    r = run_once(client, "c", "t", "s")
    assert r.parse_failed is True and r.steps_used == 3
    assert r.parse_retries == 3
    assert len(client.messages) == 3
    for messages in client.messages[1:]:
        assert sum(m["content"] == FORMAT_GUIDANCE for m in messages) == 1
    assert all(m["content"] != "garbage" for messages in client.messages for m in messages)


def test_unparseable_recovery_resets_consecutive_limit(monkeypatch):
    monkeypatch.setattr("injeval.agent.save_note", lambda **kw: "ok")
    bad = Action("unparseable", raw="garbage")
    client = FakeClient([bad, bad, Action("tool", "save_note", {"title": "t", "body": "b"}),
                         bad, bad, Action("final", text="done")])
    r = run_once(client, "c", "t", "s")
    assert r.parse_failed is False and r.final_answer == "done"
    assert r.parse_retries == 4
    assert all(sum(m["content"] == FORMAT_GUIDANCE for m in messages) <= 1
               for messages in client.messages)


def test_unparseable_at_step_budget_is_parse_failed():
    r = run_once(FakeClient([Action("unparseable")]), "c", "t", "s", max_steps=1)
    assert r.parse_failed is True and r.parse_retries == 1
    assert r.max_steps == 1


@pytest.mark.parametrize("error", [RuntimeError("model unavailable"), ValueError("bad response")])
def test_model_exception_is_recorded_without_propagating(error):
    class FailingClient(FakeClient):
        def act(self, messages):
            raise error

    r = run_once(FailingClient([]), "c", "t", "s")
    assert r.run_error == f"{type(error).__name__}: {error}"
    assert r.steps_used == 1
    assert r.parse_failed is False


def test_tool_error_is_an_observation(monkeypatch):
    def fail(**kw):
        raise ValueError("bad title")
    monkeypatch.setattr("injeval.agent.save_note", fail)
    client = FakeClient([Action("tool", "save_note", {"title": "t", "body": "b"}),
                         Action("final", text="done")])
    assert run_once(client, "c", "t", "s").final_answer == "done"
    assert "bad title" in client.messages[1][-1]["content"]
