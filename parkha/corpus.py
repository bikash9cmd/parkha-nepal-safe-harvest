"""The advisory notes and a small lexical retriever over them.

Thirteen notes, about 4,000 words. At this size a vector database is a cost with no benefit:
BM25 plus the crop and pest tags (resolved by the lexicon, which is what makes "गोलभेडामा
टुटा" and "tuta on tomato" the same query) is measured in docs/EVALUATION.md. The interface is one function, so an embedding retriever (Titan Text
Embeddings V2, or a Bedrock Knowledge Base on S3 Vectors) can replace it when the corpus grows.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import config, lexicon

_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "is", "my", "i", "it", "for", "what", "how",
    "can", "do", "with", "be", "are", "ma", "ko", "ra", "le", "ke", "cha", "chha", "मा", "को", "र", "ले", "के", "छ",
}  # fmt: skip


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    crops: tuple[str, ...]
    pests: tuple[str, ...]
    sources: tuple[str, ...]
    summary: str
    steps_en: tuple[str, ...]
    steps_ne: tuple[str, ...]

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.summary}\n" + "\n".join(self.steps_en)


def _parse(path: Path) -> Note:
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    sections: dict[str, list[str]] = {}
    current = None
    for line in body.strip().splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None and line.strip():
            sections[current].append(line.strip())

    def tags(v: str) -> tuple[str, ...]:
        return tuple(t.strip() for t in v.split(";") if t.strip())

    return Note(
        id=meta["id"],
        title=meta["title"],
        crops=tags(meta["crops"]),
        pests=tags(meta["pests"]),
        sources=tags(meta["sources"]),
        summary=" ".join(sections.get("Summary", [])),
        steps_en=tuple(s.lstrip("- ") for s in sections.get("Steps", [])),
        steps_ne=tuple(s.lstrip("- ") for s in sections.get("चरणहरू", [])),
    )


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class Corpus:
    def __init__(self, notes: list[Note]):
        self.notes = notes
        self.by_id = {n.id: n for n in notes}
        self._docs = [Counter(tokens(n.text)) for n in notes]
        self._len = [sum(d.values()) for d in self._docs]
        self._avg = sum(self._len) / len(self._len)
        df = Counter(t for d in self._docs for t in d)
        n = len(notes)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    @classmethod
    def load(cls, folder: Path = config.CORPUS_DIR) -> Corpus:
        return cls([_parse(p) for p in sorted(folder.glob("*.md"))])

    def _bm25(self, q: list[str], i: int, k1: float = 1.4, b: float = 0.75) -> float:
        d, score = self._docs[i], 0.0
        for t in q:
            if t in d:
                tf = d[t]
                score += self._idf[t] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * self._len[i] / self._avg))
        return score

    def search(self, query: str, crop: str | None = None, pest: str | None = None, k: int = config.TOP_K_NOTES):
        """Notes ranked for a question. Crop and pest come from the lexicon when not given."""
        crop = crop or next(iter(lexicon.crops(query)), None)
        pest = pest or next(iter(lexicon.pests(query)), None)
        # Canonical English names join the query, so a Nepali question scores against English notes.
        chems = lexicon.chemicals(query)
        q = tokens(query) + tokens(crop or "") + tokens(pest or "") + [t for c in chems for t in tokens(c)]
        scored = []
        for i, note in enumerate(self.notes):
            s = self._bm25(q, i)
            if pest and pest in note.pests:
                s += 6.0
            if crop and crop in note.crops:
                s += 3.0
            if "all" in note.crops and not pest:
                s += 0.5  # general notes win only when no specific pest is named
            scored.append((s, note))
        scored.sort(key=lambda x: -x[0])
        return [n for s, n in scored[:k] if s > 0]


@lru_cache(maxsize=1)
def default_corpus() -> Corpus:
    return Corpus.load()
