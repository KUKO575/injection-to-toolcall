from pathlib import Path

import pytest

from injeval.tools import ATTACKER_PORT, BENIGN_PORT, TOOL_SCHEMAS, save_note


def test_save_note_writes_inside_sandbox(tmp_path):
    path = Path(save_note("t", "b", sandbox=tmp_path))
    assert path.read_text(encoding="utf-8") == "b"
    assert tmp_path in path.parents


@pytest.mark.parametrize("title", ["../../escape", "..\\..\\escape"])
def test_save_note_rejects_path_traversal_in_title(tmp_path, title):
    with pytest.raises(ValueError):
        save_note(title, "b", sandbox=tmp_path)


def test_save_note_slugifies_title_and_preserves_unicode_body(tmp_path):
    path = Path(save_note("My note!", "메모", sandbox=tmp_path))
    assert path.name == "my-note.md"
    assert path.read_text(encoding="utf-8") == "메모"


def test_tool_ports_and_schemas():
    assert (BENIGN_PORT, ATTACKER_PORT) == (8731, 8732)
    schemas = {schema["function"]["name"]: schema for schema in TOOL_SCHEMAS}
    assert set(schemas) == {"save_note", "fetch_reference"}
    assert schemas["save_note"]["function"]["parameters"]["required"] == ["title", "body"]
    assert schemas["fetch_reference"]["function"]["parameters"]["required"] == ["url"]
