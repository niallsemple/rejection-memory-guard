import json

import pytest

from rmg import config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ["RMG_LLM_BASE_URL", "RMG_LLM_BASE", "RMG_LLM_URL", "RMG_LLM_MODEL",
                 "RMG_EMBED_MODEL", "RMG_LLM_API_KEY", "RMG_EMBEDDINGS",
                 "RMG_LLM_DISABLE_THINKING"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RMG_OFFLINE", "1")


def test_defaults_preserve_local_llama_server():
    assert config.base_url() == "http://127.0.0.1:8080/v1"
    assert config.chat_url() == "http://127.0.0.1:8080/v1/chat/completions"
    assert config.chat_model() == "qwen3.8-27b"
    assert config.embed_model() is None
    assert config.api_key() is None
    assert config.use_embeddings() is False
    assert config.disable_thinking() is True
    assert config.headers() == {"Content-Type": "application/json"}


def test_overrides(monkeypatch):
    monkeypatch.setenv("RMG_LLM_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("RMG_LLM_MODEL", "llama3.2")
    monkeypatch.setenv("RMG_EMBED_MODEL", "nomic-embed-text")
    monkeypatch.setenv("RMG_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("RMG_EMBEDDINGS", "1")
    assert config.base_url() == "http://localhost:11434/v1"
    assert config.chat_url() == "http://localhost:11434/v1/chat/completions"
    assert config.chat_model() == "llama3.2"
    assert config.embed_model() == "nomic-embed-text"
    assert config.use_embeddings() is True
    assert config.headers()["Authorization"] == "Bearer sk-test"


def test_legacy_base_and_chat_url(monkeypatch):
    monkeypatch.setenv("RMG_LLM_BASE", "http://legacy:1234/v1")
    assert config.base_url() == "http://legacy:1234/v1"
    monkeypatch.setenv("RMG_LLM_URL", "http://other/v1/chat/completions")
    assert config.chat_url() == "http://other/v1/chat/completions"


def test_openai_skips_thinking_kwargs(monkeypatch):
    monkeypatch.setenv("RMG_LLM_BASE_URL", "https://api.openai.com/v1")
    assert config.disable_thinking() is False
    monkeypatch.setenv("RMG_LLM_DISABLE_THINKING", "1")
    assert config.disable_thinking() is True


def test_embedder_uses_config(monkeypatch):
    from rmg.similarity import Embedder
    monkeypatch.setenv("RMG_LLM_BASE_URL", "http://example:9/v1")
    monkeypatch.setenv("RMG_EMBED_MODEL", "embed-x")
    e = Embedder()
    assert e.base_url == "http://example:9/v1"
    assert e.model == "embed-x"


def test_llm_refine_request(monkeypatch):
    """_llm_refine posts to the configured URL with model, key and no network in tests."""
    from rmg import extract
    monkeypatch.setenv("RMG_OFFLINE", "0")
    monkeypatch.setenv("RMG_LLM_BASE_URL", "http://example:9/v1")
    monkeypatch.setenv("RMG_LLM_MODEL", "my-model")
    monkeypatch.setenv("RMG_LLM_API_KEY", "sk-abc")
    seen = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            body = {"choices": [{"message": {"content": '{"idea": "copy wallets", "reason": "edge decays"}'}}]}
            return json.dumps(body).encode()

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["payload"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(extract.urllib.request, "urlopen", fake_urlopen)
    assert extract._llm_refine("idea", "reason", "raw") == ("copy wallets", "edge decays")
    assert seen["url"] == "http://example:9/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-abc"
    assert seen["payload"]["model"] == "my-model"
    assert seen["payload"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_api_check_embeddings_opt_in(monkeypatch):
    from rmg import api
    monkeypatch.setattr(api, "_EMBEDDER", None)
    assert api._embedder() is None  # default off
    monkeypatch.setenv("RMG_EMBEDDINGS", "1")
    assert api._embedder() is None  # still off while RMG_OFFLINE=1
    monkeypatch.setenv("RMG_OFFLINE", "0")
    assert api._embedder() is not None
