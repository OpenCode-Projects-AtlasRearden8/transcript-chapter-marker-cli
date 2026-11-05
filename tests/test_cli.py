"""End-to-end CLI tests: everything runs offline; the LLM path uses the stub."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from transcript_chapter_marker import cli
from . import FIXTURES

TS_FILE = str(FIXTURES / "timestamped.txt")
SRT_FILE = str(FIXTURES / "sample.srt")

TITLE_REPLY = {
    "choices": [
        {"message": {"content": json.dumps({"titles": ["Welcome", "Setup", "Chat"]})}}
    ]
}


def run_cli(argv, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["tcm", *argv])
    code = cli.main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


class StubHandler(BaseHTTPRequestHandler):
    reply = TITLE_REPLY

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        json.loads(self.rfile.read(length) or b"{}")
        payload = json.dumps(self.reply).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture()
def stub_url():
    server = HTTPServer(("127.0.0.1", 0), StubHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_cli_default_all_formats(monkeypatch, capsys):
    code, out, _err = run_cli([TS_FILE], monkeypatch, capsys)
    assert code == 0
    assert "Chapters\n00:00 " in out
    assert "05:12 " in out
    assert "Audiobook chapters\n00:00:00 - Chapter 1:" in out
    assert "Topics" in out


def test_cli_clickable(monkeypatch, capsys):
    _, out, _ = run_cli(
        [TS_FILE, "--format", "index", "--clickable", "https://youtu.be/v1"], monkeypatch, capsys
    )
    assert "[00:00](https://youtu.be/v1?t=0s)" in out
    assert "[05:12](https://youtu.be/v1?t=312s)" in out


def test_cli_srt_input(monkeypatch, capsys):
    code, out, _ = run_cli([SRT_FILE, "--format", "index"], monkeypatch, capsys)
    assert code == 0
    assert out.startswith("Chapters\n00:00 ")


def test_cli_plain_without_timestamps(monkeypatch, capsys):
    _, out, _ = run_cli(
        [str(FIXTURES / "plain_no_ts.txt"), "--format", "index"], monkeypatch, capsys
    )
    assert "(no timestamps; pass --interval)" in out
    assert "--:--" in out


def test_cli_interval_distribution(monkeypatch, capsys):
    _, out, _ = run_cli(
        [str(FIXTURES / "plain_no_ts.txt"), "--format", "index",
         "--interval", "1:00", "--target-min", "1"],
        monkeypatch,
        capsys,
    )
    assert "01:00 " in out and "(no timestamps" not in out


def test_cli_offset(monkeypatch, capsys):
    _, out, _ = run_cli(
        [TS_FILE, "--format", "index", "--offset", "0:10"], monkeypatch, capsys
    )
    assert "00:10 " in out


def test_cli_stdin(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin", type("FakeStdin", (), {"read": staticmethod(lambda: "[0:00] hi\n[1:00] mode state logs\n[2:00] cameras photo\n")})()
    )
    code = cli.main(["-", "--format", "index"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Chapters\n00:00 " in out


def test_cli_out_file(monkeypatch, capsys, tmp_path):
    target = tmp_path / "desc.txt"
    code, out, _ = run_cli([TS_FILE, "--out", str(target)], monkeypatch, capsys)
    assert code == 0
    assert target.read_text(encoding="utf-8").startswith("Chapters\n")
    assert "wrote" in out


def test_cli_llm_naming(monkeypatch, capsys, stub_url):
    code, out, _ = run_cli(
        [
            TS_FILE,
            "--format", "index",
            "--target-min", "3",
            "--llm",
            "--llm-base-url", stub_url,
            "--llm-model", "test-model",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    assert "Welcome" in out and "Setup" in out and "Chat" in out


def test_cli_llm_remote_http_refused(monkeypatch, capsys, stub_url, tmp_path):
    # remote plaintext http must be refused; offline titles remain
    code, out, err = run_cli(
        [
            TS_FILE,
            "--format", "index",
            "--target-min", "1",
            "--llm",
            "--llm-base-url", "http://example.com/v1",
            "--llm-model", "m",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    assert "keeping offline keyword titles" in err


def test_cli_llm_unreachable(monkeypatch, capsys):
    _, out, err = run_cli(
        [
            TS_FILE,
            "--format", "index",
            "--target-min", "1",
            "--llm",
            "--llm-base-url", "http://127.0.0.1:1/v1",
            "--llm-timeout", "1",
        ],
        monkeypatch,
        capsys,
    )
    assert "offline titles" in err


def test_cli_missing_file(monkeypatch, capsys):
    with pytest.raises(Exception):
        run_cli(["not-a-file.txt", "--format", "index"], monkeypatch, capsys)
