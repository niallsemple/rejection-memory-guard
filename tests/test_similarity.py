import os
import pytest

# Set RMG_OFFLINE=1 before importing similarity to ensure offline mode
os.environ["RMG_OFFLINE"] = "1"

from rmg.similarity import (
    tokenize,
    tfidf_similarity,
    concepts,
    Embedder,
    similarity,
    CONCEPT_SYNONYMS,
)

class TestSimilarity:
    def setup_method(self):
        """Ensure RMG_OFFLINE is set for each test."""
        os.environ["RMG_OFFLINE"] = "1"
    
    def test_tokenize_basic(self):
        tokens = tokenize("Poll the API every second")
        assert "poll" in tokens
        assert "api" in tokens
        assert "second" in tokens
    
    def test_tokenize_stopwords_removed(self):
        tokens = tokenize("the a an and or but")
        assert len(tokens) == 0
    
    def test_tokenize_stemming(self):
        tokens = tokenize("polling")
        assert "poll" in tokens
    
    def test_concepts_copy_trading(self):
        text = "copy wallets"
        found = concepts(text)
        assert "copy_trading" in found
    
    def test_concepts_polling(self):
        text = "poll the api every second"
        found = concepts(text)
        assert "polling" in found
    
    def test_concepts_websocket(self):
        text = "use websocket for streaming"
        found = concepts(text)
        assert "websocket" in found
    
    def test_concepts_fallback(self):
        text = "use fallback when disconnected"
        found = concepts(text)
        assert "fallback" in found
    
    def test_concepts_unrelated(self):
        text = "bake a chocolate cake"
        found = concepts(text)
        assert "copy_trading" not in found
        assert "polling" not in found
    
    def test_polling_paraphrases_similar(self):
        """Polling paraphrases should score > 0.5 pairwise."""
        texts = [
            "poll the API every second",
            "hit the REST endpoint once a second",
            "query the endpoint at 1 Hz",
        ]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                score = similarity(texts[i], texts[j])
                assert score > 0.5, f"Expected > 0.5, got {score} for {texts[i]} vs {texts[j]}"
    
    def test_copy_trading_paraphrases_similar(self):
        """Copy-trading paraphrases should all contain concept 'copy_trading' and score > 0.5 against 'copy profitable wallets'."""
        base = "copy profitable wallets"
        paraphrases = [
            "copy wallets",
            "mirror traders",
            "follow whales",
            "duplicate trades from top addresses",
        ]
        
        # All should contain copy_trading concept
        for text in paraphrases + [base]:
            found = concepts(text)
            assert "copy_trading" in found, f"Expected copy_trading in {text}"
        
        # All should score > 0.5 against base
        for text in paraphrases:
            score = similarity(text, base)
            assert score > 0.5, f"Expected > 0.5, got {score} for {text} vs {base}"
    
    def test_unrelated_texts_dissimilar(self):
        """Unrelated texts should score < 0.3."""
        score = similarity("bake a chocolate cake", "poll the API every second")
        assert score < 0.3, f"Expected < 0.3, got {score}"
    
    def test_embedder_returns_none_offline(self):
        """Embedder should return None when offline."""
        embedder = Embedder()
        result = embedder.embed(["test text"])
        assert result is None
    
    def test_similarity_with_embedder_offline(self):
        """Similarity should work with embedder when offline (falls back to TF-IDF)."""
        embedder = Embedder()
        score = similarity("poll the API every second", "hit the REST endpoint once a second", embedder)
        assert score > 0.5
    
    def test_tfidf_similarity_basic(self):
        """Basic TF-IDF similarity test."""
        score = tfidf_similarity("poll the api", "poll the api")
        assert score > 0.9
    
    def test_tfidf_similarity_different(self):
        """Different texts should have lower similarity."""
        score = tfidf_similarity("bake a cake", "poll the api")
        assert score < 0.5
    
    def test_concept_overlap_boost(self):
        """Concept overlap should boost similarity."""
        # These share the polling concept
        score_with_concept = similarity("poll the api every second", "hit the endpoint per second")
        # These don't share concepts
        score_without_concept = similarity("bake a cake with sugar", "mix flour and water")
        assert score_with_concept > score_without_concept

    def test_concepts_copy_trading_variants(self):
        """Test various copy trading paraphrases."""
        texts = [
            "mirror the top traders",
            "follow whales",
            "duplicate trades from top addresses",
            "copy wallets",
            "replicate what smart money wallets do",
            "shadow the biggest whale positions",
        ]
        for text in texts:
            found = concepts(text)
            assert "copy_trading" in found, f"Expected copy_trading in {text}"

    def test_concepts_polling_variants(self):
        """Test various polling paraphrases."""
        texts = [
            "hit the REST endpoint once a second",
            "query the endpoint at 1 Hz",
        ]
        for text in texts:
            found = concepts(text)
            assert "polling" in found, f"Expected polling in {text}"

    def test_concepts_none(self):
        """Test that unrelated texts have no concepts."""
        found = concepts("bake a chocolate cake")
        assert len(found) == 0

    def test_concepts_no_false_positive(self):
        """Test that verb without object doesn't trigger concept."""
        found = concepts("follow the documentation")
        assert "copy_trading" not in found
