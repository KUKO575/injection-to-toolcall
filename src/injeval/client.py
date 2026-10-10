"""Single-action model interface; malformed model output remains measurable."""

from dataclasses import dataclass
import json
import re
from typing import Literal

from injeval.tools import TOOL_SCHEMAS


# Temporary default: change after measuring both models' interface reliability.
INTERFACE: str = "json"


@dataclass
class Action:
    kind: Literal["tool", "final", "unparseable"]
    tool_name: str | None = None
    arguments: dict | None = None
    text: str | None = None
    raw: str = ""


def _strip_thinking(raw: str) -> str:
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()


def _tool_action(name, arguments, raw: str) -> Action:
    for schema in TOOL_SCHEMAS:
        function = schema["function"]
        if name != function["name"] or not isinstance(arguments, dict):
            continue
        parameters = function["parameters"]
        if any(key not in arguments for key in parameters["required"]):
            break
        if any(key not in parameters["properties"] or not isinstance(value, str)
               for key, value in arguments.items()):
            break
        return Action("tool", tool_name=name, arguments=arguments, raw=raw)
    return Action("unparseable", raw=raw)


def parse_json_action(raw: str) -> Action:
    try:
        value = json.loads(_strip_thinking(raw))
    except (ValueError, TypeError, RecursionError):
        return Action("unparseable", raw=raw)
    if isinstance(value, dict):
        if set(value) == {"final"} and isinstance(value["final"], str):
            return Action("final", text=value["final"], raw=raw)
        if set(value) == {"tool", "arguments"}:
            return _tool_action(value["tool"], value["arguments"], raw)
    return Action("unparseable", raw=raw)


class ModelClient:
    def __init__(self, model: str, temperature: float, interface: str):
        if interface not in {"native", "json"}:
            raise ValueError("interface must be native or json")
        self.model = model
        self.temperature = temperature
        self.interface = interface

    def act(self, messages: list[dict]) -> Action:
        import ollama

        request = {"model": self.model, "messages": list(messages),
                   "options": {"temperature": self.temperature}, "stream": False}
        if self.model.split(":", 1)[0] == "qwen3":
            request["think"] = False
        if self.interface == "native":
            request["tools"] = TOOL_SCHEMAS
        else:
            instruction = (
                'Return exactly one JSON action: {"tool":"NAME","arguments":{...}} '
                'or {"final":"answer"}. Use only these tool schemas: '
                + json.dumps(TOOL_SCHEMAS)
            )
            request["messages"] = [{"role": "system", "content": instruction}] + list(messages)
            request["format"] = "json"
        response = ollama.chat(**request)
        if hasattr(response, "model_dump"):
            response = response.model_dump(mode="json")
        raw = json.dumps(response, ensure_ascii=False, default=str)
        try:
            message = response["message"]
            content = message.get("content", "")
            if not isinstance(content, str):
                return Action("unparseable", raw=raw)
            if self.interface == "json":
                return parse_json_action(content)
            calls = message.get("tool_calls") or []
            if calls:
                if not isinstance(calls, list) or len(calls) != 1:
                    return Action("unparseable", raw=raw)
                function = calls[0]["function"]
                return _tool_action(function["name"], function["arguments"], raw)
            text = _strip_thinking(content)
            if not text or "<think>" in text or "</think>" in text:
                return Action("unparseable", raw=raw)
            return Action("final", text=text, raw=raw)
        except (KeyError, TypeError, AttributeError):
            return Action("unparseable", raw=raw)
