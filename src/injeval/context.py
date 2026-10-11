"""Fixed local municipal corpus and deterministic within-document insertion."""

from pathlib import Path
import re

import yaml

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CLEAN_DOCUMENTS = tuple(f"clean{i}.md" for i in range(1, 5))


def load_tasks() -> list[dict]:
    with (DATA_DIR / "tasks.yaml").open(encoding="utf-8") as stream:
        tasks = yaml.safe_load(stream)
    return [{**task, "document": (DATA_DIR / "documents" / task["document"]).read_text(encoding="utf-8")}
            for task in tasks]


def load_injections() -> list[dict]:
    with (DATA_DIR / "injections.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def build_context(task_id: str, injection_id: str | None, position: str, dilution: int) -> str:
    if position not in {"top", "middle", "bottom"}:
        raise ValueError(f"Unknown position: {position}")
    if dilution not in {1, 5}:
        raise ValueError("dilution must be 1 or 5")
    tasks = {task["id"]: task for task in load_tasks()}
    if task_id not in tasks:
        raise ValueError(f"Unknown task: {task_id}")
    document = tasks[task_id]["document"]
    if injection_id is not None:
        injections = load_injections()
        by_id = {item["id"]: item for item in injections}
        by_id.update({f"i{n}": item for n, item in enumerate(injections, 1)})
        if injection_id not in by_id:
            raise ValueError(f"Unknown injection: {injection_id}")
        injection = by_id[injection_id]
        if injection["framing"] == "prose":
            paragraphs = list(re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", document))
            index = {"top": 0, "middle": len(paragraphs) // 2,
                     "bottom": len(paragraphs) - 1}[position]
            paragraph = paragraphs[index]
            offset = paragraph.start() + len(paragraph.group().rstrip())
            document = document[:offset] + " " + injection["text"] + document[offset:]
        elif position == "top":
            offset = 0
        elif position == "bottom":
            offset = len(document)
        else:
            # Insert between paragraphs, nearest the document's character midpoint.
            boundaries = [match.end() for match in re.finditer(r"\n\n", document)]
            offset = min(boundaries, key=lambda n: abs(n - len(document) / 2))
        if injection["framing"] != "prose":
            prefix = document[:offset]
            separator = "\n" * max(0, 2 - (len(prefix) - len(prefix.rstrip("\n")))) if prefix else ""
            document = prefix + separator + injection["text"] + "\n\n" + document[offset:]
    sections = [f"## Document {task_id}\n{document}"]
    if dilution == 5:
        sections.extend(f"## Document {Path(name).stem}\n" +
                        (DATA_DIR / "documents" / name).read_text(encoding="utf-8")
                        for name in CLEAN_DOCUMENTS)
    return "\n\n".join(sections)
