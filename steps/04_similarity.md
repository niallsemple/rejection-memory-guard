Implement step 4 of SPEC.md: text similarity. Create `rmg/similarity.py` and `tests/test_similarity.py`.

Requirements:
- Pure-Python TF-IDF cosine similarity (no sklearn, no numpy required): `tokenize(text)` (lowercase, split on non-alphanumerics, drop a small stopword list, simple stemming: strip trailing "ing","ed","es","s" when word length > 4), `tfidf_similarity(a, b, corpus=None) -> float in [0,1]`.
- `CONCEPT_SYNONYMS`: dict mapping a canonical concept key to synonym phrases, used to normalise text before comparison. Must include at least:
  - "copy_trading": copy wallets, copy trading, copy-trade, mirror traders, mirror trades, follow whales, whale following, duplicate trades, top addresses, smart money, copy top wallets
  - "polling": poll, polling, poll the api, hit the endpoint, query the endpoint, every second, once a second, 1 hz, per second, refresh repeatedly, request in a loop
  - "websocket": websocket, websockets, ws stream, push stream, streaming subscription
  - "fallback": fallback, fall back, only on disconnect, backup when disconnected
- `concepts(text) -> set[str]`: concept keys present.
- `class Embedder`: `__init__(base_url=None, model=None, timeout=5)`; base_url defaults to env `RMG_LLM_BASE` or `http://127.0.0.1:8080/v1`. `embed(texts) -> list[list[float]] | None` POSTs to `{base_url}/embeddings` with urllib; returns None on any error. If env `RMG_OFFLINE=1`, never call the network and return None. Cache the "unavailable" state after first failure.
- `similarity(a, b, embedder=None) -> float`: if embedder returns vectors use cosine of embeddings averaged with TF-IDF on concept-normalised text; otherwise TF-IDF on concept-normalised text (replace synonym phrases by the concept key before tokenising). Add a concept-overlap boost: Jaccard of concepts(a), concepts(b) blended in (score = max(tfidf, 0.5*tfidf + 0.5*jaccard)).

Tests (set `RMG_OFFLINE=1` with monkeypatch in an autouse fixture): polling paraphrases ("poll the API every second" vs "hit the REST endpoint once a second" vs "query the endpoint at 1 Hz") score > 0.5 pairwise; copy-trading paraphrases ("copy wallets", "mirror traders", "follow whales", "duplicate trades from top addresses") all contain concept "copy_trading" and score > 0.5 against "copy profitable wallets"; unrelated texts ("bake a chocolate cake" vs "poll the API every second") score < 0.3; Embedder returns None offline.
