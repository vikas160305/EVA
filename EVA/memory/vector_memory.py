"""Zero-dependency local Vector RAG Memory Store for MARK-L.

Provides fast semantic retrieval (top-k search) across past sessions, projects, identity,
and personal notes using a numpy-backed term-frequency & character n-gram embedding index.
Completely free, offline, and lightweight.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


class VectorMemoryStore:
    """Lightweight, zero-dependency Vector Store using term-frequency embeddings."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path
        self.documents: List[Dict[str, Any]] = []
        self.vocabulary: Dict[str, int] = {}
        self.vectors: List[np.ndarray] = []
        if self.storage_path and self.storage_path.exists():
            self.load()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\w+", text.lower())
        # Generate word tokens + character 3-grams for semantic fuzzy matching
        ngrams = []
        for word in words:
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    ngrams.append(f"ng_{word[i:i+3]}")
        return words + ngrams

    def _build_vocab(self) -> None:
        vocab_set = set()
        for doc in self.documents:
            tokens = self._tokenize(doc["content"])
            vocab_set.update(tokens)
        self.vocabulary = {token: idx for idx, token in enumerate(sorted(vocab_set))}
        
        # Build document vectors
        self.vectors = []
        vocab_size = len(self.vocabulary)
        if vocab_size == 0:
            return

        for doc in self.documents:
            vec = np.zeros(vocab_size, dtype=np.float32)
            tokens = self._tokenize(doc["content"])
            for t in tokens:
                if t in self.vocabulary:
                    vec[self.vocabulary[t]] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            self.vectors.append(vec)

    def add_document(self, category: str, key: str, content: str, metadata: dict | None = None) -> None:
        """Add or update a document in the vector store."""
        if not content or not content.strip():
            return
        
        # Remove existing document with same key/category if present
        self.documents = [d for d in self.documents if not (d["category"] == category and d["key"] == key)]
        
        self.documents.append({
            "category": category,
            "key": key,
            "content": content,
            "metadata": metadata or {}
        })
        self._build_vocab()
        if self.storage_path:
            self.save()

    def search(self, query: str, top_k: int = 3, category: str | None = None) -> List[Tuple[Dict[str, Any], float]]:
        """Search for top-k semantically relevant documents matching the query."""
        if not self.documents or not self.vocabulary or not self.vectors:
            return []

        query_tokens = self._tokenize(query)
        q_vec = np.zeros(len(self.vocabulary), dtype=np.float32)
        for t in query_tokens:
            if t in self.vocabulary:
                q_vec[self.vocabulary[t]] += 1.0
        
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        results = []
        for idx, doc in enumerate(self.documents):
            if category and doc["category"] != category:
                continue
            doc_vec = self.vectors[idx]
            similarity = float(np.dot(q_vec, doc_vec))
            if similarity > 0.0001:
                results.append((doc, similarity))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "documents": self.documents
        }
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.documents = data.get("documents", [])
            self._build_vocab()
        except Exception as e:
            print(f"[VectorMemory] ⚠️ Load error: {e}")
