from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import urlsplit


class RecordingListener:
    def __init__(self, port: int, body: bytes, status: int):
        self.port = port
        self.body = body
        self.status = status
        self._hits: list[dict] = []
        self._lock = Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    @property
    def hits(self) -> list[dict]:
        with self._lock:
            return [hit.copy() for hit in self._hits]

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()

    def start(self) -> None:
        if self._server is not None:
            return
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def _respond(self):
                parts = urlsplit(self.path)
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                with listener._lock:
                    listener._hits.append({
                        "method": self.command,
                        "path": parts.path,
                        "query": parts.query,
                        "body": body.decode("utf-8", errors="replace"),
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
                self.send_response(listener.status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(listener.body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(listener.body)

            do_GET = _respond
            do_POST = _respond
            do_PUT = _respond
            do_DELETE = _respond
            do_PATCH = _respond
            do_HEAD = _respond
            do_OPTIONS = _respond

            def log_message(self, format, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
        self._server = None
        self._thread = None
