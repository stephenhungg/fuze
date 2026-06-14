"""local vector memory adapter backed by ollama embeddings and qdrant."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx

from .db import store


COLLECTION = os.getenv("FUZE_QDRANT_COLLECTION", "fuze_context")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("FUZE_EMBED_MODEL", "nomic-embed-text")
VECTOR_SIZE = 768


def stable_point_id(text_id: str) -> int:
    digest = hashlib.sha256(text_id.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def fallback_embedding(text: str, size: int = VECTOR_SIZE) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < size:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) == size:
                break
        digest = hashlib.sha256(digest).digest()
    return values


async def embed(text: str) -> tuple[list[float], str]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
            )
            response.raise_for_status()
            vector = response.json().get("embedding", [])
        if len(vector) == VECTOR_SIZE:
            return vector, "ollama:nomic-embed-text"
    except Exception:
        pass
    return fallback_embedding(text), "deterministic-fallback"


async def status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{QDRANT_URL}/healthz")
            response.raise_for_status()
            collections = await client.get(f"{QDRANT_URL}/collections")
            collections.raise_for_status()
        names = [item["name"] for item in collections.json().get("result", {}).get("collections", [])]
        return {
            "available": True,
            "host": QDRANT_URL,
            "collection": COLLECTION,
            "seeded": COLLECTION in names,
        }
    except Exception as exc:
        return {"available": False, "host": QDRANT_URL, "collection": COLLECTION, "seeded": False, "error": str(exc)}


async def seed() -> dict[str, Any]:
    chunks = store.chunks()
    points = []
    embedding_source = "unknown"
    for chunk in chunks:
        vector, embedding_source = await embed(chunk["text"])
        points.append(
            {
                "id": stable_point_id(chunk["id"]),
                "vector": vector,
                "payload": {
                    "chunk_id": chunk["id"],
                    "title": chunk["title"],
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "sensitivity": chunk.get("sensitivity", "internal"),
                    "external_output_allowed": chunk.get("external_output_allowed", False),
                    "citations": chunk.get("citations", []),
                    "allowed_roles": chunk.get("allowed_roles", []),
                    "metadata": chunk.get("metadata", {}),
                },
            }
        )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            create = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION}",
                json={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}},
            )
            if create.status_code != 409:
                create.raise_for_status()
            upsert = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION}/points",
                json={"points": points},
            )
            upsert.raise_for_status()
        return {
            "available": True,
            "collection": COLLECTION,
            "points": len(points),
            "embedding_source": embedding_source,
        }
    except Exception as exc:
        return {
            "available": False,
            "collection": COLLECTION,
            "points": 0,
            "embedding_source": embedding_source,
            "error": str(exc),
        }


async def search(query: str, limit: int = 5) -> dict[str, Any]:
    vector, embedding_source = await embed(query)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
                json={"vector": vector, "limit": limit, "with_payload": True},
            )
            response.raise_for_status()
        hits = response.json().get("result", [])
        return {
            "available": True,
            "collection": COLLECTION,
            "embedding_source": embedding_source,
            "hits": [
                {
                    "score": hit.get("score"),
                    "chunk_id": hit.get("payload", {}).get("chunk_id"),
                    "title": hit.get("payload", {}).get("title"),
                    "source": hit.get("payload", {}).get("source"),
                    "sensitivity": hit.get("payload", {}).get("sensitivity"),
                    "external_output_allowed": hit.get("payload", {}).get("external_output_allowed"),
                }
                for hit in hits
            ],
        }
    except Exception as exc:
        return {
            "available": False,
            "collection": COLLECTION,
            "embedding_source": embedding_source,
            "hits": [],
            "error": str(exc),
        }
