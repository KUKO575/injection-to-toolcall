from urllib.request import Request, urlopen

from injeval.listeners import RecordingListener
from injeval.tools import fetch_reference


def test_listener_records_query_and_returns_configured_body():
    listener = RecordingListener(port=8899, body=b"REFERENCE OK", status=200)
    listener.start()
    try:
        assert fetch_reference("http://127.0.0.1:8899/ref?id=ABC123") == "REFERENCE OK"
    finally:
        listener.stop()
    hit = listener.hits[0]
    assert hit["query"] == "id=ABC123"
    assert hit["method"] == "GET"
    assert hit["path"] == "/ref"
    assert hit["body"] == ""
    assert hit["ts"]


def test_attacker_listener_returns_empty_body():
    listener = RecordingListener(port=8900, body=b"", status=200)
    listener.start()
    try:
        assert fetch_reference("http://127.0.0.1:8900/x") == ""
    finally:
        listener.stop()


def test_listener_binds_loopback_records_post_and_clears():
    listener = RecordingListener(port=0, body=b"accepted", status=201)
    listener.start()
    try:
        host, port = listener._server.server_address
        assert host == "127.0.0.1"
        request = Request(f"http://127.0.0.1:{port}/note?q=1", data=b"hello")
        with urlopen(request, timeout=5) as response:
            assert response.status == 201
            assert response.read() == b"accepted"
        assert listener.hits[0]["method"] == "POST"
        assert listener.hits[0]["body"] == "hello"
        listener.clear()
        assert listener.hits == []
    finally:
        listener.stop()
