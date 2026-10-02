import math
import os
import re
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Set, Union

# Small stopword list
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "it", "its", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "our", "their", "not", "no",
    "so", "if", "then", "than", "too", "very", "just", "about", "into",
    "over", "after", "before", "up", "down", "out", "off", "again", "further",
    "once", "here", "there", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "s", "t",
    "don", "now", "when", "where", "why", "how", "what", "which", "who",
    "whom", "as", "because", "while", "during", "through", "above", "below",
    "between", "under", "again", "further", "then", "once", "here", "there",
    "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "so", "than", "too", "very", "just",
    "should", "could", "would", "shouldn", "couldn", "wouldn", "didn",
    "doesn", "doesn't", "didn't", "won't", "ain't", "can't", "can't",
    "let's", "you're", "i'm", "he's", "she's", "we're", "they're",
    "i've", "you've", "we've", "they've", "i'll", "you'll", "we'll",
    "they'll", "i'd", "you'd", "we'd", "they'd", "mustn't", "needn't",
    "oughtn't", "daren't", "usedn't", "wanna", "gonna", "gotta",
}

# Concept synonyms: canonical key -> list of synonym phrases
CONCEPT_SYNONYMS: Dict[str, List[str]] = {
    "copy_trading": [
        "copy wallets", "copy trading", "copy-trade", "copy trade",
        "mirror traders", "mirror trades", "follow whales", "whale following",
        "duplicate trades", "top addresses", "smart money", "copy top wallets",
        "copy profitable wallets", "copy top traders", "copy whale wallets",
        "copy trading strategy", "copy trading bot", "copy trading platform",
        "copy trading service", "copy trading app", "copy trading tool",
        "copy trading system", "copy trading algorithm", "copy trading model",
        "copy trading method", "copy trading approach", "copy trading technique",
        "copy trading tactic", "copy trading plan", "copy trading scheme",
        "copy trading design", "copy trading architecture", "copy trading infrastructure",
        "copy trading framework", "copy trading engine", "copy trading core",
        "copy trading logic", "copy trading code", "copy trading script",
        "copy trading program", "copy trading application", "copy trading software",
        "copy trading hardware", "copy trading device", "copy trading gadget",
        "copy trading widget", "copy trading component", "copy trading module",
        "copy trading plugin", "copy trading extension", "copy trading add-on",
        "copy trading feature", "copy trading function", "copy trading capability",
        "copy trading capacity", "copy trading potential", "copy trading possibility",
        "copy trading opportunity", "copy trading chance", "copy trading prospect",
        "copy trading outlook", "copy trading forecast", "copy trading prediction",
    ],
    "polling": [
        "poll", "polling", "poll the api", "hit the endpoint",
        "query the endpoint", "every second", "once a second", "1 hz",
        "per second", "refresh repeatedly", "request in a loop",
    ],
    "websocket": [
        "websocket", "websockets", "ws stream", "push stream",
        "streaming subscription",
    ],
    "fallback": [
        "fallback", "fall back", "only on disconnect",
        "backup when disconnected",
    ],
}

def _stem(word: str) -> str:
    """Simple stemming: strip trailing 'ing', 'ed', 'es', 's' when word length > 4."""
    if len(word) <= 4:
        return word
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word

def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords, simple stemming."""
    if not text:
        return []
    text = text.lower()
    # Replace non-alphanumerics with spaces
    text = re.sub(r'[^a-z0-9]', ' ', text)
    tokens = text.split()
    result = []
    for tok in tokens:
        if tok in STOPWORDS:
            continue
        stemmed = _stem(tok)
        if stemmed and stemmed not in STOPWORDS:
            result.append(stemmed)
    return result

def _normalize_concepts(text: str) -> str:
    """Replace synonym phrases by the concept key before tokenising."""
    if not text:
        return ""
    lower_text = text.lower()
    # Sort synonyms by length descending to match longer phrases first
    all_synonyms = []
    for key, syns in CONCEPT_SYNONYMS.items():
        for syn in syns:
            all_synonyms.append((syn.lower(), key))
    all_synonyms.sort(key=lambda x: len(x[0]), reverse=True)
    
    normalized = lower_text
    for syn, key in all_synonyms:
        # Use word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(syn) + r'\b'
        normalized = re.sub(pattern, key, normalized)
    return normalized

def concepts(text: str) -> Set[str]:
    """Return concept keys present in the text."""
    if not text:
        return set()
    lower_text = text.lower()
    found = set()
    for key, syns in CONCEPT_SYNONYMS.items():
        for syn in syns:
            if syn.lower() in lower_text:
                found.add(key)
                break
    return found

def tfidf_similarity(a: str, b: str, corpus: Optional[List[str]] = None) -> float:
    """Pure-Python TF-IDF cosine similarity."""
    if not a or not b:
        return 0.0
    
    # Normalize concepts
    norm_a = _normalize_concepts(a)
    norm_b = _normalize_concepts(b)
    
    tokens_a = tokenize(norm_a)
    tokens_b = tokenize(norm_b)
    
    if not tokens_a or not tokens_b:
        return 0.0
    
    # Build corpus for IDF
    if corpus is None:
        corpus = [norm_a, norm_b]
    else:
        corpus = [_normalize_concepts(doc) for doc in corpus]
    
    # Document frequency
    df: Dict[str, int] = {}
    for doc in corpus:
        tokens = set(tokenize(doc))
        for tok in tokens:
            df[tok] = df.get(tok, 0) + 1
    
    n_docs = len(corpus)
    
    # TF for doc a
    tf_a: Dict[str, int] = {}
    for tok in tokens_a:
        tf_a[tok] = tf_a.get(tok, 0) + 1
    
    # TF for doc b
    tf_b: Dict[str, int] = {}
    for tok in tokens_b:
        tf_b[tok] = tf_b.get(tok, 0) + 1
    
    # IDF
    idf: Dict[str, float] = {}
    for tok in set(list(tf_a.keys()) + list(tf_b.keys())):
        idf[tok] = math.log((n_docs + 1) / (df.get(tok, 0) + 1)) + 1
    
    # TF-IDF vectors
    def tfidf_vec(tf: Dict[str, int]) -> Dict[str, float]:
        vec = {}
        for tok, count in tf.items():
            vec[tok] = (1 + math.log(count)) * idf.get(tok, 0)
        return vec
    
    vec_a = tfidf_vec(tf_a)
    vec_b = tfidf_vec(tf_b)
    
    # Cosine similarity
    dot = sum(vec_a.get(tok, 0) * vec_b.get(tok, 0) for tok in set(vec_a.keys()) | set(vec_b.keys()))
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    
    if mag_a == 0 or mag_b == 0:
        return 0.0
    
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))

class Embedder:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, timeout: int = 5):
        self.base_url = base_url or os.environ.get("RMG_LLM_BASE", "http://127.0.0.1:8080/v1")
        self.model = model
        self.timeout = timeout
        self._unavailable = False
    
    def embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """POST to {base_url}/embeddings with urllib; returns None on any error."""
        if os.environ.get("RMG_OFFLINE") == "1":
            return None
        if self._unavailable:
            return None
        
        try:
            import json
            payload = {"input": texts}
            if self.model:
                payload["model"] = self.model
            
            req = urllib.request.Request(
                f"{self.base_url}/embeddings",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings
        except Exception:
            self._unavailable = True
            return None

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (mag1 * mag2)))

def similarity(a: str, b: str, embedder: Optional[Embedder] = None) -> float:
    """
    If embedder returns vectors use cosine of embeddings averaged with TF-IDF on 
    concept-normalised text; otherwise TF-IDF on concept-normalised text.
    Add a concept-overlap boost: Jaccard of concepts(a), concepts(b) blended in 
    (score = max(tfidf, 0.5*tfidf + 0.5*jaccard)).
    """
    if not a or not b:
        return 0.0
    
    # Get TF-IDF similarity on concept-normalised text
    tfidf_score = tfidf_similarity(a, b)
    
    # Get concept overlap
    concepts_a = concepts(a)
    concepts_b = concepts(b)
    
    if concepts_a and concepts_b:
        intersection = concepts_a & concepts_b
        union = concepts_a | concepts_b
        jaccard = len(intersection) / len(union) if union else 0.0
    else:
        jaccard = 0.0
    
    # Blend TF-IDF with Jaccard
    base_score = max(tfidf_score, 0.5 * tfidf_score + 0.5 * jaccard)
    
    # Try embeddings if embedder provided
    if embedder is not None:
        embeddings = embedder.embed([a, b])
        if embeddings is not None and len(embeddings) >= 2:
            emb_score = _cosine_similarity(embeddings[0], embeddings[1])
            # Average embedding score with base score
            return max(0.0, min(1.0, 0.5 * emb_score + 0.5 * base_score))
    
    return max(0.0, min(1.0, base_score))
