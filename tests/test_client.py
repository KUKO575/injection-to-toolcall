from types import SimpleNamespace

import pytest

from injeval.client import INTERFACE, ModelClient, parse_json_action
from injeval.tools import TOOL_SCHEMAS


def test_json_interface_parses_tool_action():
    a = parse_json_action('{"tool":"fetch_reference","arguments":{"url":"http://x"}}')
    assert a.kind == "tool" and a.tool_name == "fetch_reference"
    assert a.arguments == {"url": "http://x"}


def test_json_interface_marks_garbage_unparseable_without_raising():
    a = parse_json_action("I think I should probably fetch the thing.")
    assert a.kind == "unparseable" and a.raw.startswith("I think")


def test_json_interface_parses_final_answer():
    assert parse_json_action('{"final":"done"}').text == "done"


def test_qwen_thinking_is_stripped_before_parsing():
    raw = '<think>maybe fetch</think>{"final":"no"}'
    a = parse_json_action(raw)
    assert a.kind == "final" and a.text == "no" and a.raw == raw


@pytest.mark.parametrize("raw", ['[]', 'null', '{}', '{"final":3}',
    '{"tool":"unknown","arguments":{}}', '{"tool":"fetch_reference","arguments":[]}',
    '{"tool":"fetch_reference","arguments":{}}',
    '{"final":"done","tool":"fetch_reference","arguments":{"url":"x"}}',
    '<think>unfinished{"final":"done"}'])
def test_malformed_actions_are_unparseable(raw):
    assert parse_json_action(raw).kind == "unparseable"


@pytest.fixture
def fake_ollama(monkeypatch):
    calls = []
    response = {"message": {"content": '{"final":"done"}'}}

    def chat(**kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setitem(__import__("sys").modules, "ollama", SimpleNamespace(chat=chat))
    return calls, response


def test_json_client_sends_format_schemas_temperature_and_disables_qwen_thinking(fake_ollama):
    calls, _ = fake_ollama
    messages = [{"role": "user", "content": "Write a note."}]
    assert ModelClient("qwen3:8b", 0.7, "json").act(messages).kind == "final"
    assert messages == [{"role": "user", "content": "Write a note."}]
    request = calls[0]
    assert request["think"] is False and request["options"] == {"temperature": 0.7}
    assert request["format"] == "json"
    assert "fetch_reference" in request["messages"][0]["content"]
    assert "tools" not in request
    assert INTERFACE == "json"


def test_native_client_parses_tool_call(fake_ollama):
    calls, response = fake_ollama
    response["message"] = {"content": "", "tool_calls": [
        {"function": {"name": "fetch_reference", "arguments": {"url": "http://127.0.0.1:8731/ref"}}}]}
    a = ModelClient("llama3.1:8b", 0.7, "native").act([])
    assert a.kind == "tool" and a.tool_name == "fetch_reference"
    assert calls[0]["tools"] == TOOL_SCHEMAS and "think" not in calls[0]
    assert "fetch_reference" in a.raw


def test_native_multiple_calls_are_unparseable(fake_ollama):
    _, response = fake_ollama
    call = {"function": {"name": "save_note", "arguments": {"title": "t", "body": "b"}}}
    response["message"] = {"content": "", "tool_calls": [call, call]}
    assert ModelClient("llama3.1:8b", 0.7, "native").act([]).kind == "unparseable"


def test_native_final_strips_thinking(fake_ollama):
    _, response = fake_ollama
    response["message"] = {"content": "<think>reason</think>done"}
    assert ModelClient("qwen3:8b", 0.7, "native").act([]).text == "done"


def test_client_rejects_unknown_interface():
    with pytest.raises(ValueError):
        ModelClient("llama3.1:8b", 0.7, "other")
