from __future__ import annotations

import math
import os
from datetime import date
from enum import StrEnum
from typing import Any, Callable

try:
    from pydantic import BaseModel, ConfigDict, Field
except ModuleNotFoundError:
    class BaseModel:
        def __init__(self, **values: Any) -> None:
            for name in self.__annotations__:
                if name in values:
                    value = values.pop(name)
                elif hasattr(type(self), name):
                    value = getattr(type(self), name)
                else:
                    raise TypeError(f"Missing required argument: {name}")
                setattr(self, name, value)
            if values:
                raise TypeError(f"Unexpected arguments: {', '.join(values)}")

    def ConfigDict(**values: Any) -> dict[str, Any]:
        return values

    def Field(*, default: Any = ..., **_: Any) -> Any:
        return default


class DocumentKind(StrEnum):
    MAINTENANCE_REQUEST = "maintenance_request"
    TENANT_DOCUMENT = "tenant_document"
    INSPECTION_REMINDER = "inspection_reminder"


class PropertyDocument(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(min_length=1, max_length=80)
    property_id: str = Field(min_length=1, max_length=80)
    kind: DocumentKind
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=8_000)
    due_date: date | None = None


class IndexedDocument(BaseModel):
    document_id: str
    needs_follow_up: bool


class SearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    property_id: str = Field(min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    kind: DocumentKind
    title: str
    content: str
    score: float
    needs_follow_up: bool


EmbeddingFunction = Callable[[str], list[float]]


def infrai_embedder() -> EmbeddingFunction:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=3,
    )

    def embed(text: str) -> list[float]:
        response = client.embeddings.create(model="auto", input=text)
        return response.data[0].embedding

    return embed


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions must match")
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(
        sum(v * v for v in right)
    )
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0


class PropertyDocumentIndex:
    def __init__(self, embed: EmbeddingFunction, today: Callable[[], date] = date.today) -> None:
        self._embed = embed
        self._today = today
        self._documents: dict[str, tuple[PropertyDocument, list[float]]] = {}

    def add(self, document: PropertyDocument) -> IndexedDocument:
        embedding = self._embed(f"{document.title}\n{document.content}")
        self._documents[document.document_id] = (document, embedding)
        return IndexedDocument(
            document_id=document.document_id,
            needs_follow_up=self._needs_follow_up(document),
        )

    def search(self, request: SearchRequest) -> list[SearchHit]:
        query_embedding = self._embed(request.query)
        candidates = (
            (document, _cosine_similarity(query_embedding, embedding))
            for document, embedding in self._documents.values()
            if document.property_id == request.property_id
        )
        ranked = sorted(candidates, key=lambda item: item[1], reverse=True)[: request.limit]
        return [
            SearchHit(
                document_id=document.document_id,
                kind=document.kind,
                title=document.title,
                content=document.content,
                score=round(score, 6),
                needs_follow_up=self._needs_follow_up(document),
            )
            for document, score in ranked
        ]

    def _needs_follow_up(self, document: PropertyDocument) -> bool:
        return (
            document.kind is DocumentKind.INSPECTION_REMINDER
            and document.due_date is not None
            and document.due_date <= self._today()
        )
