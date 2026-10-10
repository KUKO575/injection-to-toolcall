from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


BENIGN_PORT = 8731
ATTACKER_PORT = 8732


def save_note(title: str, body: str, *, sandbox: Path = Path("sandbox")) -> str:
    root = Path(sandbox).resolve()
    candidate = (root / title).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Title leaves the sandbox")
    slug = re.sub(r"[^\w-]+", "-", title.lower()).strip("-_")
    if not slug:
        raise ValueError("Title must contain a filename character")
    path = (root / f"{slug}.md").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Note path leaves the sandbox")
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return str(path)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_reference(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "http" or parts.hostname != "127.0.0.1":
        raise ValueError("Reference URL must use HTTP on 127.0.0.1")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(url, timeout=10) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8")


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note in the local sandbox and return its path.",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_reference",
            "description": "Fetch a reference from the local loopback HTTP server.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
]
