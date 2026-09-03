def format_chunks_for_prompt(chunks):
    if not chunks:
        return ""

    lines = ["以下是和当前问题相关的知识库参考资料，请结合这些资料回答，但不要机械照抄：\n"]

    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"[资料{index}]")
        lines.append(f"来源：{chunk['title']}")
        lines.append(f"内容：{chunk['content']}")
        lines.append("")

    return "\n".join(lines)

from rag.retriever import retrieve_chunks

if __name__ == "__main__":
    chunks = retrieve_chunks("我想练牙医的治疗节奏", top_k=3)
    result = format_chunks_for_prompt(chunks)
    print(result)