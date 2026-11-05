"""Tests for the optional LLM naming path using a local stub endpoint."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from transcript_chapter_marker import llm
from transcript_chapter_marker.chapters import build_chapters
from transcript_chapter_marker.intake import parse_text
from transcript_chapter_marker.llm import (
    LLMError,
    UnsafeEndpointError,
    chat_completion,
    _json_titles,
    check_endpoint,
    name_chapters,
)
from . import FIXTURES

TITLE_REPLY = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {"titles": ["Outline Notes", "Workshop Welcome", "Ollama Install", "Modelfiles", "Privacy"]}
                )
            }
        }
    ]
}


class StubHandler(BaseHTTPRequestHandler):
    reply = TITLE_REPLY

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        assert self.path.startswith("/v1/chat/completions")
        assert "model" in body and body["messages"]
        if self.headers.get("Authorization"):
            self.last_auth = self.headers["Authorization"]
        payload = json.dumps(self.reply).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence
        pass


@pytest.fixture()
def stub_url():
    server = HTTPServer(("127.0.0.1", 0), StubHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_check_endpoint_rejects_remote_http():
    with pytest.raises(UnsafeEndpointError):
        check_endpoint("http://example.com/v1")
    check_endpoint("http://localhost:11434/v1")
    check_endpoint("http://127.0.0.1:8080/v1")
    check_endpoint("https://example.com/v1")
    with pytest.raises(UnsafeEndpointError):
        check_endpoint("ftp://example.com/v1")


def test_json_titles_parses_fenced_reply():
    assert _json_titles('```json\n{"titles":["A","B"]}\n```') == ["A", "B"]
    assert _json_titles("Sure!\n{\"titles\": [\"Hello\", \"World\"]}") == ["Hello", "World"]


def test_json_titles_bad_reply_raises():
    with pytest.raises(LLMError):
        _json_titles("no json here")


def test_chat_completion_posts_json(stub_url):
    out = chat_completion(
        stub_url,
        "test-model",
        [{"role": "user", "content": "hi"}],
        timeout=5,
    )
    assert "Workshop Welcome" in out


def test_name_chapters_replaces_titles(stub_url):
    t = parse_text((FIXTURES / "plain_no_ts.txt").read_text(encoding="utf-8"))
    chs = build_chapters(t.segments, target_minutes=1.0, had_timestamps=False)
    titles = name_chapters(chs, 400, stub_url, "test-model", timeout=5)
    assert titles == ["Outline Notes", "Workshop Welcome", "Ollama Install", "Modelfiles", "Privacy"]


def test_name_chapters_wrong_count_raises(stub_url, monkeypatch):
    monkeypatch.setattr(StubHandler, "reply",
                        {"choices": [{"message": {"content": '{"titles": ["only one"]}'}}]})
    t = parse_text((FIXTURES / "plain_no_ts.txt").read_text(encoding="utf-8"))
    chs = build_chapters(t.segments, target_minutes=1.0, had_timestamps=False)
    with pytest.raises(LLMError):
        name_chapters(chs, 400, stub_url, "test-model", timeout=5)


def test_no_env_key_needed(stub_url, monkeypatch):
    monkeypatch.delenv(llm._API_KEY_ENV, raising=False)
    out = chat_completion(stub_url, "m", [{"role": "user", "content": "x"}])
    assert out  # key-less request works against a key-less server
