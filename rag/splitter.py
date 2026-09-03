from typing import Optional

from rag.loader import get_documents_signature, load_documents

CHUNK_CACHE = {}


def split_documents(game_name: Optional[str] = "dwrg"):
    cache_key = game_name or "__pure_chat__"
    signature = get_documents_signature(game_name)
    cached = CHUNK_CACHE.get(cache_key)

    if cached and cached["signature"] == signature:
        return cached["chunks"]

    documents = load_documents(game_name)
    chunks = []

    for doc in documents:
        parts = doc["content"].split("\n\n")

        for index, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            chunks.append({
                "source": doc["source"],
                "title": doc["title"],
                "chunk_id": f'{doc["title"]}_{index}',
                "content": part
            })

    CHUNK_CACHE[cache_key] = {
        "signature": signature,
        "chunks": chunks,
    }

    return chunks
