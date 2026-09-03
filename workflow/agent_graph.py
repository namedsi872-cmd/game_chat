from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from shared_managers import long_term_memory_manager, role_memory_manager
# from workflow.router_intent import router_intent


class AgentState(TypedDict):
    user_id: int
    role_name: str
    session_id: int
    game_name: Optional[str]
    message: str
    intent: str
    intent_reason: str
    now_mode: str
    final_mode: str
    full_history: list


def is_draw_request(message: str) -> bool:
    draw_phrases = (
        "帮我画",
        "画一张",
        "画个",
        "画一幅",
        "生成图片",
        "生成一张图",
        "生成一幅图",
        "绘制",
        "作图",
        "生图",
    )
    return any(phrase in message for phrase in draw_phrases)


def intent_node(state: AgentState) -> AgentState:
    # result = router_intent(state["message"], state["now_mode"])
    # state["intent"] = result["intent"]
    # state["intent_reason"] = result["reason"]
    # state["final_mode"] = result["final_mode"]
    if is_draw_request(state["message"]):
        state["intent"] = "draw"
        state["intent_reason"] = "检测到明确的绘图请求"
        state["final_mode"] = "draw"
    else:
        state["intent"] = "chat"
        state["intent_reason"] = "默认普通聊天"
        state["final_mode"] = "chat"
    return state


def load_memory_node(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    role_name = state["role_name"]
    session_id = state["session_id"]

    # 每次请求都按当前 session 重建短时记忆，避免新会话串到旧会话
    role_memory = role_memory_manager.load_memory(user_id, role_name, session_id)

    # 长期记忆只在训练 / 复盘模式下参与，普通聊天不要强行带入训练信息
    long_term_history = []
    if state["final_mode"] in ("training", "review"):
        long_term_history = long_term_memory_manager.build_long_term_history(
            user_id, role_name, limit=3
        )

    short_history = role_memory.get_messages()
    state["full_history"] = long_term_history + short_history
    return state


graph_builder = StateGraph(AgentState)
graph_builder.add_node("intent_node", intent_node)
graph_builder.add_node("load_memory_node", load_memory_node)

graph_builder.add_edge(START, "intent_node")
graph_builder.add_edge("intent_node", "load_memory_node")
graph_builder.add_edge("load_memory_node", END)

graph = graph_builder.compile()
