from typing import Optional

from rag.splitter import split_documents


def score_chunk(query, chunk):
    score = 0

    keywords = ["牙医", "治疗", "走位", "拉点", "救人", "地图", "追击", "监管", "求生者"]

    for keyword in keywords:
        if keyword in query and keyword in chunk["content"]:
            score += 2
        if keyword in query and keyword in chunk["title"]:
            score += 1

    if query in chunk["content"]:
        score += 3

    return score


def retrieve_chunks(
    query,
    game_name: Optional[str] = "dwrg",
    top_k=3
):
    chunks = split_documents(game_name)
    scored_chunks = []

    for chunk in chunks:
        score = score_chunk(query, chunk)
        if score > 0:
            scored_chunks.append({
                "score": score,
                "chunk": chunk
            })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    return [item["chunk"] for item in scored_chunks[:top_k]]

if __name__ == "__main__":
    results = retrieve_chunks("我想练牙医的治疗节奏", top_k=3)
    for item in results:
        print(item)
