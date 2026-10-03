import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from rmg.models import Record
from rmg.ledger import Ledger
from rmg.web import render_index, render_record, make_handler


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")


@pytest.fixture
def ledger(tmp_path):
    path = str(tmp_path / "test.db")
    l = Ledger(path)
    yield l
    l.close()


def test_render_index(ledger):
    r1 = Record(canonical_idea="Idea A", rejection_reason="Reason A", reconsider_if="If X")
    r2 = Record(canonical_idea="Idea B", rejection_reason="Reason B", reconsider_if="If Y")
    ledger.add(r1)
    ledger.add(r2)

    html = render_index(ledger)
    assert "Idea A" in html
    assert "Idea B" in html
    assert "ACTIVE" in html


def test_render_record(ledger):
    r1 = Record(canonical_idea="Idea A", rejection_reason="Reason A", reconsider_if="If X")
    ledger.add(r1)

    html = render_record(ledger, r1.id)
    assert html is not None
    assert "Reason A" in html
    assert "created" in html
    assert "If X" in html


def test_escaping(ledger):
    r1 = Record(canonical_idea="<script>x</script>", rejection_reason="Reason")
    ledger.add(r1)

    html = render_index(ledger)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_api(ledger):
    r1 = Record(canonical_idea="Idea A", rejection_reason="Reason A")
    r2 = Record(canonical_idea="Idea B", rejection_reason="Reason B")
    ledger.add(r1)
    ledger.add(r2)

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(ledger))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/api/records"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            assert len(data) == 2
            assert data[0]["canonical_idea"] in ["Idea A", "Idea B"]
    finally:
        server.shutdown()
        thread.join()
