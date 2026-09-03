import json
from typing import Any

from langchain_core.tools import tool

from backend.database import SessionLocal
from backend.models import ChatMessage, ChatSession
from role_loader import normalize_role_name
from shared_managers import role_memory_manager


def collect_doubao_messages(node: Any, result: list[dict]) -> None:
    if isinstance(node, list):
        for item in node:
            collect_doubao_messages(item, result)
        return

    if isinstance(node, dict):
        raw_role = (node.get("role") or node.get("speaker") or "").lower()
        text = (node.get("text") or "").strip()

        if raw_role in ("user", "assistant", "agent") and text:
            role = "assistant" if raw_role == "agent" else raw_role
            result.append({
                "role": role,
                "content": text,
            })

        for value in node.values():
            if isinstance(value, (dict, list)):
                collect_doubao_messages(value, result)


@tool
def import_external_chat_history(
    user_id: int,
    role_name: str,
    raw_json_text: str,
) -> dict:
    """
    导入外部聊天记录到当前智能体中。

    Args:
        user_id: 当前登录用户的 ID。
        role_name: 当前使用的角色名，例如 "yagami_light"。
        raw_json_text: 外部聊天记录文件的原始 json 文本。

    Returns:
        导入结果说明，包含新会话 id 和导入条数。
    """
    role_name = normalize_role_name(role_name)
    raw_data = json.loads(raw_json_text)

    messages = []
    collect_doubao_messages(raw_data, messages)

    valid_messages = []
    for item in messages:
        if item["role"] in ("user", "assistant") and item["content"]:
            valid_messages.append(item)

    if not valid_messages:
        return {
            "ok": False,
            "message": "导入失败：没有解析到有效消息。",
        }

    db = SessionLocal()
    try:
        # 导入外部历史时，新建一个会话承接这批消息
        chat_session = ChatSession(
            user_id=user_id,
            role_name=role_name,
            title="豆包导入会话",
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        for item in valid_messages:
            db.add(
                ChatMessage(
                    session_id=chat_session.id,
                    role=item["role"],
                    content=item["content"],
                )
            )

        db.commit()

        # 把数据库里的历史同步回短时记忆
        role_memory_manager.load_memory(
            user_id=user_id,
            role_name=role_name,
            session_id=chat_session.id,
        )

        return {
            "ok": True,
            "message": "聊天记录导入成功",
            "session_id": chat_session.id,
            "imported_count": len(valid_messages),
            "title": chat_session.title,
        }
    finally:
        db.close()
