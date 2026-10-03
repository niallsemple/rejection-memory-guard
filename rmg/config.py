"""LLM / embeddings endpoint configuration, read from environment variables.

RMG talks to any OpenAI-compatible server (llama.cpp ``llama-server``, Ollama,
LM Studio, vLLM, OpenAI itself, ...). Everything is optional: with no server
reachable, or with ``RMG_OFFLINE=1``, RMG falls back to pure-Python TF-IDF + rules.

Environment variables
---------------------
RMG_LLM_BASE_URL   Base URL of the OpenAI-compatible API (default ``http://127.0.0.1:8080/v1``).
                   ``RMG_LLM_BASE`` is accepted as a legacy alias.
RMG_LLM_URL        Full chat-completions URL override (default ``{base}/chat/completions``).
RMG_LLM_MODEL      Chat model name used to tidy extracted rejections (default ``qwen3.8-27b``;
                   llama.cpp's single-model server ignores it).
RMG_EMBED_MODEL    Embedding model name sent to ``{base}/embeddings`` (default: none sent).
RMG_LLM_API_KEY    API key sent as ``Authorization: Bearer ...`` (default: none).
RMG_EMBEDDINGS     ``1`` to blend server embeddings into ``api.check``/``rmg check`` matching
                   (default off: matching is TF-IDF + concept rules only).
RMG_LLM_DISABLE_THINKING
                   ``1`` (default, except for api.openai.com) sends
                   ``chat_template_kwargs: {enable_thinking: false}`` for Qwen-style templates;
                   ``0`` omits it.
RMG_OFFLINE        ``1`` disables all network calls.
"""
import os
from typing import Dict, Optional
from urllib.parse import urlparse

DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_CHAT_MODEL = "qwen3.8-27b"


def _env(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def offline() -> bool:
    return os.environ.get("RMG_OFFLINE") == "1"


def base_url() -> str:
    url = _env("RMG_LLM_BASE_URL") or _env("RMG_LLM_BASE") or DEFAULT_BASE_URL
    return url.rstrip("/")


def chat_url() -> str:
    return _env("RMG_LLM_URL") or f"{base_url()}/chat/completions"


def chat_model() -> str:
    return _env("RMG_LLM_MODEL") or DEFAULT_CHAT_MODEL


def embed_model() -> Optional[str]:
    return _env("RMG_EMBED_MODEL")


def api_key() -> Optional[str]:
    return _env("RMG_LLM_API_KEY")


def use_embeddings() -> bool:
    return os.environ.get("RMG_EMBEDDINGS") == "1"


def disable_thinking() -> bool:
    flag = _env("RMG_LLM_DISABLE_THINKING")
    if flag is not None:
        return flag not in ("0", "false", "False", "no")
    host = urlparse(chat_url()).hostname or ""
    return host != "api.openai.com"


def headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    key = api_key()
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h
