"""Offline keyphrase extraction used for chapter titles and the topics list."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List, Sequence, Tuple

from .words import KEPT_MIN_LEN, STOPWORDS

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'&-]*")


def tokens(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def kept_tokens(text: str) -> List[str]:
    return [
        w for w in tokens(text)
        if w not in STOPWORDS and len(w) >= KEPT_MIN_LEN
    ]


def keyphrases(texts: Sequence[str]) -> Tuple[Counter, Counter, defaultdict]:
    """Return (unigram counts, bigram counts, first-seen position).

    Bigrams only count when the two words are adjacent in the original text,
    so punctuation/stopword gaps ("set up a small language model") do not
    fabricate pairs like "set small" or "a small".
    """
    tf: Counter = Counter()
    bf: Counter = Counter()
    first: defaultdict = defaultdict(lambda: 10**9)
    pos = 0
    for t in texts:
        raw = [w.lower() for w in _WORD_RE.findall(t)]
        kept_flags = [
            w not in STOPWORDS and len(w) >= KEPT_MIN_LEN for w in raw
        ]
        for i, (w, keep) in enumerate(zip(raw, kept_flags)):
            if keep:
                tf[w] += 1
                first[w] = min(first[w], pos)
                pos += 1
            if (
                keep
                and i + 1 < len(raw)
                and kept_flags[i + 1]
            ):
                b = f"{w} {raw[i + 1]}"
                bf[b] += 1
                first[b] = min(first[b], pos)
                pos += 1
    return tf, bf, first


def top_terms(
    texts: Sequence[str],
    n: int = 10,
    min_count: int = 1,
) -> List[Tuple[str, int]]:
    """Ranked keyphrases, preferring repeated bigrams over single words."""
    tf, bf, first = keyphrases(texts)
    strong_bigrams = [(b, c) for b, c in bf.items() if c >= max(2, min_count)]
    words = [(w, c) for w, c in tf.items() if c >= min_count]

    # Drop a unigram when it is dominated by a chosen bigram containing it.
    bigram_words = {w for b, _ in strong_bigrams for w in b.split()}
    filtered_unigrams = [(w, c) for w, c in words if w not in bigram_words]

    scored = [(-(2 * c), first[b], b, c) for b, c in strong_bigrams] + [
        (-c, first[w], w, c) for w, c in filtered_unigrams
    ]
    scored.sort(key=lambda item: (item[0], item[1]))

    out: Dict[str, int] = {}
    for _neg_score, _pos, phrase, count in scored:
        phrase_words = set(phrase.split())
        if any(phrase_words & set(p.split()) for p in out):
            continue  # avoid overlapping suggestions
        out[phrase] = count
        if len(out) >= n:
            break
    return [(p, c) for p, c in out.items()]


def title_case(phrase: str) -> str:
    small = {"and", "or", "the", "of", "a", "an", "for", "to", "in", "on"}
    return " ".join(
        w if w in small and i else w.capitalize()
        for i, w in enumerate(phrase.split())
    )
