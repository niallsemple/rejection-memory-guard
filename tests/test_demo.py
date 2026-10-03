import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo import run_demo


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")


def test_demo(tmp_path):
    out = run_demo(str(tmp_path / "d.db"), verbose=False)

    assert out["result"]["decision"] == "BLOCK"
    assert "edge decays" in out["result"]["reason"].lower()
    assert "REJECTED APPROACHES — DO NOT REPROPOSE" in out["injection"]
    assert out["fallback"]["decision"] in ("WARN", "ALLOW")
    assert out["reconsider"]["decision"] == "RECONSIDER"
    assert "copy the trades" not in out["summary"]
