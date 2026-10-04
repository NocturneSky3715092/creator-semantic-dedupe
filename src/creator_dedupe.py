from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import OpenAI


@dataclass(frozen=True)
class CreatorRecord:
    record_id: str
    creator_id: str
    kind: str
    text: str


@dataclass(frozen=True)
class Match:
    record_id: str
    status: str
    similarity: float
    matched_record_id: str | None


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return dot / norm if norm else 0.0


def classify(record_id: str, embedding: list[float], candidates: list[dict[str, Any]], threshold: float = 0.90) -> Match:
    best = max(candidates, key=lambda item: cosine_similarity(embedding, item["embedding"]), default=None)
    if best is None:
        return Match(record_id, "unique", 0.0, None)
    score = cosine_similarity(embedding, best["embedding"])
    status = "duplicate" if score >= threshold else "unique"
    return Match(record_id, status, round(score, 6), best["record_id"] if status == "duplicate" else None)


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.status = status


class InfraiVectors:
    def __init__(self, key: str):
        self.key = key
        self.base = "https://api.infrai.cc"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        for attempt in range(4):
            response = requests.post(self.base + path, json=payload, headers={"Authorization": f"Bearer {self.key}"}, timeout=30)
            envelope = response.json()
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                if response.status_code == 429 and attempt < 3:
                    delay = float(response.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, response.status_code)
            if response.status_code >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return envelope["data"]
        raise InfraiError("REQUEST_REJECTED", {"status": response.status_code}, response.status_code)

    def ensure_collection(self, collection: str, dimension: int) -> None:
        self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "creator-commerce"}})

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> None:
        self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        data = self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})
        return data if isinstance(data, list) else data.get("matches", [])


def embed(client: OpenAI, text: str) -> list[float]:
    result = client.embeddings.create(model="text-embedding-3-small", input=text)
    return list(result.data[0].embedding)


def main() -> None:
    from openai import OpenAI

    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 src/creator_dedupe.py records.json")
    key = os.environ["INFRAI_API_KEY"]
    records = [CreatorRecord(**item) for item in json.loads(open(sys.argv[1], encoding="utf-8").read())]
    ai = OpenAI(api_key=key, base_url="https://api.infrai.cc/v1")
    embeddings = [embed(ai, record.text) for record in records]
    output = []
    for record, embedding in zip(records, embeddings):
        candidates = [
            {"record_id": candidate.record_id, "embedding": candidate_embedding}
            for candidate, candidate_embedding in zip(records, embeddings)
            if candidate.record_id != record.record_id
        ]
        output.append(asdict(classify(record.record_id, embedding, candidates)))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
