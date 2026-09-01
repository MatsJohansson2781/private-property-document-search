from functools import lru_cache

from fastapi import Depends, FastAPI

from .document_index import (
    IndexedDocument,
    PropertyDocument,
    PropertyDocumentIndex,
    SearchHit,
    SearchRequest,
    infrai_embedder,
)


@lru_cache(maxsize=1)
def build_index() -> PropertyDocumentIndex:
    return PropertyDocumentIndex(infrai_embedder())


app = FastAPI(title="Private property document search")


@app.post("/documents", response_model=IndexedDocument, status_code=201)
def index_document(
    document: PropertyDocument,
    index: PropertyDocumentIndex = Depends(build_index),
) -> IndexedDocument:
    return index.add(document)


@app.post("/search", response_model=list[SearchHit])
def search_documents(
    request: SearchRequest,
    index: PropertyDocumentIndex = Depends(build_index),
) -> list[SearchHit]:
    return index.search(request)
