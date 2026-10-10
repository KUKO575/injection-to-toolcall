"""Bounded tool loop for a single local writer run."""

from datetime import datetime, timezone
import json
from time import perf_counter

from injeval.record import RunRecord
from injeval.tools import fetch_reference, save_note


def run_once(client, context: str, task_prompt: str, system_prompt: str, max_steps: int = 6) -> RunRecord:
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    started = perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{task_prompt}\n\n{context}"}]
    prompt = json.dumps(messages, ensure_ascii=False)
    calls = []
    final_answer = ""
    parse_failed = False
    tools = {"fetch_reference": fetch_reference, "save_note": save_note}
    for step in range(1, min(max_steps, 6) + 1):
        action = client.act(messages)
        if action.kind == "unparseable":
            parse_failed = True
            break
        if action.kind == "final":
            final_answer = action.text or ""
            break
        if action.kind != "tool" or action.tool_name not in tools or not isinstance(action.arguments, dict):
            parse_failed = True
            break
        call = {"name": action.tool_name, "arguments": dict(action.arguments)}
        calls.append(call)
        try:
            observation = tools[action.tool_name](**action.arguments)
        except Exception as exc:
            observation = f"Tool error: {type(exc).__name__}: {exc}"
        if getattr(client, "interface", "json") == "native":
            messages.append({"role": "assistant", "content": "", "tool_calls": [
                {"function": call}]})
            messages.append({"role": "tool", "tool_name": action.tool_name, "content": observation})
        else:
            messages.append({"role": "assistant", "content": json.dumps(
                {"tool": action.tool_name, "arguments": action.arguments})})
            messages.append({"role": "tool", "tool_name": action.tool_name, "content": observation})
    return RunRecord("", timestamp, client.model, "", "", 0, "", "", 0,
                     client.temperature, "main", prompt, final_answer, calls, [], [],
                     step, perf_counter() - started, parse_failed)
