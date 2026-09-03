"""Groq-compatible local proxy for a local model backend.

This server exposes a small subset of the Groq/OpenAI chat API and forwards
requests to a local model backend. It is designed for clients that only know
how to talk to Groq-style endpoints.

Supported upstream providers:
- ollama: translates OpenAI-style chat requests to /api/chat
- openai: forwards OpenAI-style chat requests to a compatible /v1 backend
"""

from __future__ import annotations

import argparse
import cgi
import io
import json
import os
import re
import time
import uuid
import sys
import tempfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.voice_service import transcribe_audio as local_transcribe_audio
except Exception:
    local_transcribe_audio = None


DEFAULT_PUBLIC_MODEL = "openai/gpt-oss-120b:free"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OPENAI_URL = "http://127.0.0.1:1234/v1"
DEFAULT_BIND_PORT = 800
DEFAULT_VERITY_CONFIG = r"C:\Users\Zephy\AppData\Roaming\.minecraft\versions\1.21.1-NeoForge_21.1.248\config\verity-common.toml"


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def read_verity_toml(path: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path or not os.path.exists(path):
        return result

    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                match = re.match(r'^\s*([A-Za-z0-9_]+)\s*=\s*"(.*)"\s*$', line)
                if match:
                    result[match.group(1)] = match.group(2)
    except Exception:
        return {}

    return result


def json_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def new_chat_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex}"


def parse_json_body(raw: bytes) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - handled by caller
        raise ValueError(f"invalid JSON body: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


@dataclass
class MultipartPart:
    name: str
    filename: Optional[str]
    content_type: str
    file: io.BytesIO


def parse_multipart_body(raw: bytes, content_type: str) -> Dict[str, MultipartPart]:
    media_type, params = cgi.parse_header(content_type)
    if media_type.lower() != "multipart/form-data":
        raise ValueError(f"unsupported content type: {content_type}")

    boundary = params.get("boundary")
    if not boundary:
        raise ValueError("missing multipart boundary")

    boundary_bytes = ("--" + boundary).encode("utf-8")
    result: Dict[str, MultipartPart] = {}

    for chunk in raw.split(boundary_bytes):
        chunk = chunk.strip()
        if not chunk or chunk == b"--":
            continue

        if chunk.startswith(b"--"):
            break

        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]

        header_blob, separator, body = chunk.partition(b"\r\n\r\n")
        if not separator:
            continue

        headers: Dict[str, str] = {}
        for line in header_blob.decode("utf-8", "replace").split("\r\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        disposition = headers.get("content-disposition")
        if not disposition:
            continue
        _, disposition_params = cgi.parse_header(disposition)
        name = disposition_params.get("name")
        if not name:
            continue

        filename = disposition_params.get("filename")
        content_type_header = headers.get("content-type", "text/plain; charset=utf-8")
        result[name] = MultipartPart(
            name=name,
            filename=filename,
            content_type=content_type_header,
            file=io.BytesIO(body),
        )

    return result


def build_models_list(public_model: str) -> Dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": public_model,
                "object": "model",
                "owned_by": "local",
            }
        ],
    }


def clamp_temperature(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        temp = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(temp, 2.0))


def extract_text_from_messages(messages: Iterable[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content:
            parts.append(content)
    return "\n".join(parts)


@dataclass
class ProxyConfig:
    provider: str
    upstream_url: str
    upstream_model: str
    public_model: str
    bind_host: str
    bind_port: int

    @property
    def chat_endpoint(self) -> str:
        if self.provider == "ollama":
            return urljoin(self.upstream_url.rstrip("/") + "/", "api/chat")
        return urljoin(self.upstream_url.rstrip("/") + "/", "chat/completions")

    @property
    def models_endpoint(self) -> str:
        if self.provider == "ollama":
            return urljoin(self.upstream_url.rstrip("/") + "/", "api/tags")
        return urljoin(self.upstream_url.rstrip("/") + "/", "models")


def load_config() -> ProxyConfig:
    provider = (env("GROQ_PROXY_PROVIDER", "ollama") or "ollama").lower()
    if provider not in {"ollama", "openai"}:
        provider = "ollama"

    public_model = env("GROQ_PROXY_PUBLIC_MODEL", DEFAULT_PUBLIC_MODEL) or DEFAULT_PUBLIC_MODEL
    upstream_model = env("GROQ_PROXY_UPSTREAM_MODEL", public_model) or public_model
    bind_host = env("GROQ_PROXY_HOST", "127.0.0.1") or "127.0.0.1"
    bind_port = int(env("GROQ_PROXY_PORT", str(DEFAULT_BIND_PORT)) or str(DEFAULT_BIND_PORT))

    if provider == "openai":
        upstream_url = env("GROQ_PROXY_UPSTREAM_URL", DEFAULT_OPENAI_URL) or DEFAULT_OPENAI_URL
    else:
        upstream_url = env("GROQ_PROXY_UPSTREAM_URL", DEFAULT_OLLAMA_URL) or DEFAULT_OLLAMA_URL

    return ProxyConfig(
        provider=provider,
        upstream_url=upstream_url.rstrip("/"),
        upstream_model=upstream_model,
        public_model=public_model,
        bind_host=bind_host,
        bind_port=bind_port,
    )


def load_api_key() -> str:
    direct = env("GROQ_PROXY_API_KEY")
    if direct:
        return direct

    verity_config = env("GROQ_PROXY_VERITY_CONFIG", DEFAULT_VERITY_CONFIG) or DEFAULT_VERITY_CONFIG
    toml_values = read_verity_toml(verity_config)
    return toml_values.get("apiKey", "")


class GroqCompatHandler(BaseHTTPRequestHandler):
    server_version = "GroqCompatProxy/1.0"

    def _config(self) -> ProxyConfig:
        return self.server.config  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length > 0 else b""

    def _stream_bytes(self, chunks: Iterable[bytes]) -> None:
        for chunk in chunks:
            if not chunk:
                continue
            self.wfile.write(chunk)
            self.wfile.flush()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        config = self._config()

        if path in {"/health", "/"}:
            self._send_json(
                200,
                {
                    "status": "ok",
                    "provider": config.provider,
                    "upstream_url": config.upstream_url,
                    "public_model": config.public_model,
                    "upstream_model": config.upstream_model,
                },
            )
            return

        if path.endswith("/models") or path == "/models":
            self._send_json(200, build_models_list(config.public_model))
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        if not (
            path.endswith("/chat/completions")
            or path.endswith("/api/chat")
            or path.endswith("/audio/transcriptions")
        ):
            self._send_json(404, {"error": "not found"})
            return

        if path.endswith("/audio/transcriptions"):
            self._proxy_transcription()
            return

        raw_body = self._read_body()
        try:
            payload = parse_json_body(raw_body)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        config = self._config()
        stream = bool(payload.get("stream"))
        request_model = payload.get("model") or config.public_model

        if config.provider == "openai":
            self._proxy_openai(payload, request_model, stream)
            return

        self._proxy_ollama(payload, request_model, stream)

    def _proxy_transcription(self) -> None:
        raw_body = self._read_body()
        content_type = self.headers.get("Content-Type", "")
        if not content_type:
            self._send_json(400, {"error": "missing Content-Type header"})
            return

        try:
            form = parse_multipart_body(raw_body, content_type)
        except Exception as exc:
            self._send_json(400, {"error": f"invalid multipart body: {exc}"})
            return

        file_item = form.get("file")
        if file_item is None or not file_item.filename:
            self._send_json(400, {"error": "missing file field"})
            return

        file_bytes = file_item.file.read()
        if not file_bytes:
            self._send_json(400, {"error": "empty audio file"})
            return

        suffix = os.path.splitext(file_item.filename or "")[1] or ".wav"
        if local_transcribe_audio is None:
            self._send_json(
                501,
                {
                    "error": "local whisper backend is unavailable",
                    "hint": "install faster-whisper or run the proxy in the game_chat environment",
                },
            )
            return

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            text = local_transcribe_audio(temp_path)
            self._send_json(
                200,
                {
                    "text": text,
                },
            )
        except Exception as exc:
            self._send_json(500, {"error": f"transcription failed: {exc}"})
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _proxy_openai(self, payload: Dict[str, Any], request_model: str, stream: bool) -> None:
        config = self._config()
        incoming_auth = (self.headers.get("Authorization") or "").strip()
        api_key = load_api_key()
        if incoming_auth.lower().startswith("bearer "):
            api_key = incoming_auth[7:].strip() or api_key
        upstream_payload = dict(payload)
        upstream_payload["model"] = config.upstream_model or request_model

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = json_bytes(upstream_payload)
        request = Request(
            config.chat_endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            upstream = urlopen(request, timeout=600)
        except HTTPError as exc:
            self._send_json(exc.code, {"error": exc.read().decode("utf-8", errors="ignore")})
            return
        except URLError as exc:
            self._send_json(502, {"error": f"upstream unreachable: {exc}"})
            return

        if not stream:
            try:
                data = json.loads(upstream.read().decode("utf-8"))
            except Exception as exc:
                self._send_json(502, {"error": f"invalid upstream response: {exc}"})
                return
            self._send_json(200, data)
            return

        self._send_sse_headers(200)
        while True:
            line = upstream.readline()
            if not line:
                break
            self.wfile.write(line)
            self.wfile.flush()

    def _proxy_ollama(self, payload: Dict[str, Any], request_model: str, stream: bool) -> None:
        config = self._config()
        messages = payload.get("messages") or []
        if not isinstance(messages, list):
            self._send_json(400, {"error": "messages must be a list"})
            return

        upstream_payload: Dict[str, Any] = {
            "model": config.upstream_model or request_model,
            "messages": messages,
            "stream": stream,
        }

        temperature = clamp_temperature(payload.get("temperature"))
        if temperature is not None:
            upstream_payload["options"] = {"temperature": temperature}

        if payload.get("max_tokens") is not None:
            upstream_payload["options"] = upstream_payload.get("options", {})
            upstream_payload["options"]["num_predict"] = int(payload["max_tokens"])

        body = json_bytes(upstream_payload)
        request = Request(
            config.chat_endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            upstream = urlopen(request, timeout=600)
        except HTTPError as exc:
            self._send_json(exc.code, {"error": exc.read().decode("utf-8", errors="ignore")})
            return
        except URLError as exc:
            self._send_json(502, {"error": f"upstream unreachable: {exc}"})
            return

        if not stream:
            self._handle_ollama_non_stream_response(upstream, request_model)
            return

        self._handle_ollama_stream_response(upstream, request_model)

    def _handle_ollama_non_stream_response(self, upstream: Any, request_model: str) -> None:
        try:
            data = json.loads(upstream.read().decode("utf-8"))
        except Exception as exc:
            self._send_json(502, {"error": f"invalid upstream response: {exc}"})
            return

        content = ""
        if isinstance(data, dict):
            message = data.get("message")
            if isinstance(message, dict):
                content = message.get("content") or ""
            elif isinstance(data.get("response"), str):
                content = data["response"]

        response = {
            "id": new_chat_id(),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
        self._send_json(200, response)

    def _handle_ollama_stream_response(self, upstream: Any, request_model: str) -> None:
        self._send_sse_headers(200)
        chat_id = new_chat_id()
        created = int(time.time())

        while True:
            raw_line = upstream.readline()
            if not raw_line:
                break

            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except Exception:
                continue

            message = data.get("message") if isinstance(data, dict) else None
            chunk_text = ""
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    chunk_text = content
            elif isinstance(data, dict):
                response_text = data.get("response")
                if isinstance(response_text, str):
                    chunk_text = response_text

            if chunk_text:
                payload = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None,
                        }
                    ],
                }
                self._stream_bytes(
                    [
                        b"data: " + json_bytes(payload) + b"\n\n",
                    ]
                )

            if isinstance(data, dict) and data.get("done"):
                break

        self._stream_bytes([b"data: [DONE]\n\n"])


def run() -> None:
    config = load_config()
    server = ThreadingHTTPServer((config.bind_host, config.bind_port), GroqCompatHandler)
    server.config = config  # type: ignore[attr-defined]

    print("Groq-compatible proxy ready")
    print(f"  provider     : {config.provider}")
    print(f"  bind         : http://{config.bind_host}:{config.bind_port}")
    print(f"  upstream     : {config.upstream_url}")
    print(f"  public model : {config.public_model}")
    print(f"  upstream model: {config.upstream_model}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Groq-compatible local proxy.")
    parser.add_argument("--host", default=None, help="Bind host override")
    parser.add_argument("--port", type=int, default=None, help="Bind port override")
    args = parser.parse_args()

    if args.host:
        os.environ["GROQ_PROXY_HOST"] = args.host
    if args.port:
        os.environ["GROQ_PROXY_PORT"] = str(args.port)

    run()
