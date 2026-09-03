from llm import ask_llm, ask_llm_stream
from rag.retriever import retrieve_chunks
from rag.formatter import format_chunks_for_prompt
from role_loader import get_game_display_name
#澶勭悊璁粌宸ヤ綔娴?


def apply_game_context_prompt(current_prompt: str, game_name: str | None = None):
    if not game_name:
        return current_prompt

    game_display_name = get_game_display_name(game_name)
    current_prompt += (
        "\n\n褰撳墠浼氳瘽缁戝畾娓告垙锛?{game_display_name}銆?"
        "濡傛灉鐢ㄦ埛鎻愬埌鈥滆繖涓父鎴忊€濃€滆繖娆炬父鎴忊€濊€屾病鏈夋槑纭垏鎹紝"
        "榛樿灏辨槸鎸囪繖娆炬父鎴忋€傛櫘閫氶櫔鑱婃椂涓嶈寮鸿鎼暀绋嬫垨鐭ヨ瘑鐐癸紝"
        "鍙湪鐢ㄦ埛闂埌鐩稿叧鍐呭鏃跺啀鑷劧鍙傝€冦€?"
    ).format(game_display_name=game_display_name)
    return current_prompt


#rag璋冪敤
def rag_call(message: str, current_prompt: str, game_name: str | None = None):
    current_prompt = apply_game_context_prompt(current_prompt, game_name)

    if not game_name:
        return current_prompt

    chunks = retrieve_chunks(message, game_name=game_name)
    formatted_prompt = format_chunks_for_prompt(chunks)
    if formatted_prompt:
        current_prompt += (
            "\n\n浠ヤ笅鏄拰褰撳墠闂鐩稿叧鐨勭煡璇嗗簱鍙傝€冭祫鏂欙紝璇风粨鍚堣繖浜涜祫鏂欏洖绛旓細\n"
            + formatted_prompt
        )
    return current_prompt


def handle_training_flow(
    message: str,
    current_prompt: str,
    full_history: list,
    game_name: str | None = None,
):
    current_prompt = rag_call(message, current_prompt, game_name)
    reply = ask_llm(current_prompt, full_history)
    return reply.strip()


#娴佸紡鍝嶅簲
def handle_training_flow_stream(
    message: str,
    current_prompt: str,
    full_history: list,
    game_name: str | None = None,
):
    current_prompt = rag_call(message, current_prompt, game_name)
    yield from ask_llm_stream(current_prompt, full_history)
