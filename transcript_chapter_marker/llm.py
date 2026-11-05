"""Optional topic/chapter naming through an OpenAI-compatible chat endpoint.

Off by default. Works with any OpenAI-compatible server, e.g. local Ollama:
    ollama serve            (then)  ollama pull llama3.2
    --llm --llm-base-url http://localhost:11434/v1 --llm-model llama3.2

Privacy rules honoured here:
* Nothing leaves the machine unless the user explicitly passes --llm.
* http:// (plaintext) base URLs are only accepted for loopback addresses.
* An API key is read from the TRANSCRIPT_LLM_API_KEY environment variable if
  set; keys are never written to files or logs.
"""

from __future__ import annotations

import json
import os
import re
from ipaddress import ip_address, ip_network
from typing import List, Optional, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlparse

from .chapters import Chapter


class LLMError(RuntimeError):
    pass


class UnsafeEndpointError(LLMError):
    """Raised when a plaintext (http) endpoint is not on loopback."""


_API_KEY_ENV = "TRANSCRIPT_LLM_API_KEY"

SYSTEM_PROMPT = (
    "You name chapters for transcripts. Reply with JSON only, no prose."
)

USER_PROMPT = """Name each chapter of this transcript.

Chapters (in order):
{chapters}

Rules:
- One short, specific title per chapter, at most 6 words.
- Reply with ONLY a JSON object shaped like {{"titles": ["...", "..."]}}
  with exactly {count} titles in chapter order.
"""


def _is_loopback_url(base_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
        hostname = parsed.hostname or ""
    except ValueError:
        return False
    if parsed.scheme != "http":
        return True  # https is encrypted end to end; host does not matter here
    host = hostname.rstrip(".")
    try:
        addr = ip_address(host)
        return addr.is_loopback
    except ValueError:
        pass
    locals_ = ("localhost", "::1")
    for name in locals_:
        if host == name or host.endswith("." + name):
            return True
    try:
        net = ip_network(host, strict=False)
        return net.is_loopback
    except ValueError:
        return False


def check_endpoint(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeEndpointError(
            f"endpoint scheme must be http or https, got: {base_url!r}"
        )
    if parsed.scheme == "http" and not _is_loopback_url(base_url):
        raise UnsafeEndpointError(
            "plaintext http:// is only allowed for loopback endpoints "
            "(localhost / 127.0.0.1). Use https:// for remote servers so the "
            "transcript is never sent unencrypted."
        )


def chat_completion(
    base_url: str,
    model: str,
    messages: List[dict],
    timeout: float = 20.0,
    api_key: Optional[str] = None,
) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint."""
    url = base_url.rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    url += "/chat/completions"

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urlrequest.Request(
        url, data=payload, headers=headers, method="POST"
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        raise LLMError(f"endpoint returned HTTP {exc.code}") from None
    except urlerror.URLError as exc:
        raise LLMError(f"cannot reach endpoint: {exc.reason}") from None
    except json.JSONDecodeError:
        raise LLMError("endpoint returned invalid JSON") from None

    try:
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected response shape from endpoint") from None


def _json_titles(raw: str) -> List[str]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'"titles"\s*:\s*\[(.*?)\]', text, re.S)
        if not match:
            raise LLMError("model reply did not contain titles JSON") from None
        data = {"titles": re.findall(r'"([^"]+)"', match.group(1))}
    titles = data.get("titles") if isinstance(data, dict) else None
    if not isinstance(titles, list):
        raise LLMError("model reply missing 'titles' list")
    cleaned = []
    for t in titles:
        if not isinstance(t, str):
            continue
        t = t.strip().strip('"').replace("\n", " ")
        if t:
            cleaned.append(t[:60])
    return cleaned


def name_chapters(
    chapters: Sequence[Chapter],
    excerpt_chars: int,
    base_url: str,
    model: str,
    timeout: float = 20.0,
    api_key: Optional[str] = None,
) -> List[str]:
    """Ask the endpoint for chapter titles. Raises LLMError on any problem."""
    check_endpoint(base_url)
    api_key = api_key or os.environ.get(_API_KEY_ENV)
    parts = []
    for i, ch in enumerate(chapters, 1):
        excerpt = " ".join(s.text for s in ch.segments)[:excerpt_chars]
        if not excerpt:
            excerpt = "(empty section)"
        parts.append(f"Chapter {i}: {excerpt}")
    prompt = USER_PROMPT.format(chapters="\n".join(parts), count=len(chapters))
    raw = chat_completion(
        base_url,
        model,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        timeout=timeout,
        api_key=api_key,
    )
    titles = _json_titles(raw)
    if len(titles) != len(chapters):
        raise LLMError(
            f"expected {len(chapters)} titles, got {len(titles)}"
        )
    return titles
