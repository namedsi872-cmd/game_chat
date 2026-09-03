from typing import Optional

from role_loader import get_knowledge_base_dir

DOCUMENT_CACHE = {}


def get_documents_signature(game_name: Optional[str] = "dwrg"):
    selected_dir = get_knowledge_base_dir(game_name)
    if selected_dir is None or not selected_dir.exists():
        return None

    signature = []
    for file_path in selected_dir.iterdir():
        if file_path.suffix not in [".txt", ".md"]:
            continue

        stat = file_path.stat()
        signature.append((file_path.name, stat.st_mtime_ns, stat.st_size))

    signature.sort()
    return tuple(signature)


# 鍔犺浇鏂囨。
def load_documents(game_name: Optional[str] = "dwrg"):
    documents = []
    selected_dir = get_knowledge_base_dir(game_name)
    if selected_dir is None or not selected_dir.exists():
        return documents

    signature = get_documents_signature(game_name)
    cache_key = str(selected_dir)
    cached = DOCUMENT_CACHE.get(cache_key)

    if cached and cached["signature"] == signature:
        return cached["documents"]

    for file_path in selected_dir.iterdir():
        if file_path.suffix not in [".txt", ".md"]:
            continue

        content = file_path.read_text(encoding="utf-8")
        documents.append({
            "source": str(file_path),
            "title": file_path.stem,
            "content": content
        })

    DOCUMENT_CACHE[cache_key] = {
        "signature": signature,
        "documents": documents,
    }

    return documents


if __name__ == "__main__":
    docs = load_documents()
    print(docs)
