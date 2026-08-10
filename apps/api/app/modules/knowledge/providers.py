import hashlib
import math
import re
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...


class LLMProvider(ABC):
    @abstractmethod
    def answer(self, question: str, contexts: list[str]) -> str: ...


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding for private/offline retrieval; replaceable by OpenAI."""

    dimensions = 96

    def embed(self, text: str) -> list[float]:
        result = [0.0] * self.dimensions
        for token in re.findall(r"[\w\u0590-\u05ff]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            result[int.from_bytes(digest[:2], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in result)) or 1.0
        return [value / norm for value in result]


class ExtractiveLLMProvider(LLMProvider):
    def answer(self, question: str, contexts: list[str]) -> str:
        if not contexts:
            return "לא נמצא מידע מתאים במסמכי הסביבה."
        words = set(re.findall(r"[\w\u0590-\u05ff]+", question.lower()))
        sentences = [
            sentence.strip() for context in contexts for sentence in re.split(r"(?<=[.!?])\s+", context)
        ]
        ranked = sorted(sentences, key=lambda value: len(words & set(value.lower().split())), reverse=True)
        return " ".join(ranked[:3])[:1800]


def similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))
