from sentence_transformers import SentenceTransformer, util
from django.core.cache import cache
from .utils import save_judgment_concurrent

# Load model once globally
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# Default entailment threshold
DEFAULT_THRESHOLD = 0.8


def judge_pair(sentence1: str, sentence2: str):
    """Compute entailment and cache results."""
    # Normalize pair order (symmetry)
    key = f"judge:{sentence1.strip().lower()}::{sentence2.strip().lower()}"

    # Try cache first
    cached = cache.get(key)
    if cached:
        return cached | {"cached": True}

    # Compute similarity
    embeddings = model.encode([sentence1, sentence2], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    label = "ENTAIL" if similarity >= DEFAULT_THRESHOLD else "NO_ENTAIL"

    result = {
        "sentence1": sentence1,
        "sentence2": sentence2,
        "similarity": round(similarity, 4),
        "label": label,
        "cached": False,
    }

    # Cache result for 1 hour (3600 seconds)
    cache.set(key, result, timeout=3600)

    # Persist judgment (concurrency-safe)
    try:
        save_judgment_concurrent(sentence1, sentence2, similarity, label)
    except Exception as e:
        # Logging only — we don't fail the response if DB persistence fails,
        import logging
        logging.getLogger("judge.request").exception("Failed to persist judgment: %s", e)
    return result


def judge_bulk_pairs(pairs):
    """
    Efficiently judge multiple sentence pairs at once.
    - pairs: list of {"sentence1": str, "sentence2": str}
    Returns: list of {"sentence1", "sentence2", "similarity", "label"}
    """

    # Flatten all sentences: [s1_1, s2_1, s1_2, s2_2, ...]
    sentences = []
    for p in pairs:
        sentences.append(p['sentence1'])
        sentences.append(p['sentence2'])

    # Batch encode using Sentence-BERT
    embeddings = model.encode(sentences, convert_to_tensor=True, show_progress_bar=False)

    results = []
    for i in range(0, len(embeddings), 2):
        s1 = pairs[i // 2]['sentence1']
        s2 = pairs[i // 2]['sentence2']
        emb1 = embeddings[i]
        emb2 = embeddings[i + 1]
        similarity = util.cos_sim(emb1, emb2).item()
        label = "ENTAIL" if similarity >= DEFAULT_THRESHOLD else "NO_ENTAIL"

        result = {
            "sentence1": s1,
            "sentence2": s2,
            "similarity": round(similarity, 4),
            "label": label,
        }

        # Save each judgment safely (with concurrency protection)
        try:
            save_judgment_concurrent(s1, s2, similarity, label)
        except Exception as e:
            import logging
            logging.getLogger("judge.request").exception("Failed to persist bulk judgment: %s", e)

        results.append(result)

    return results