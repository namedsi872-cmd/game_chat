from datetime import datetime

from backend.database import SessionLocal
from backend.models import ChatMessage, Long_term_memory
from llm import ask_llm


class ShortTermMemory:
    def __init__(self, max_messages=16):
        self.max_messages = max_messages
        self.messages = []

    def add_message(self, role, content):
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        self.messages.append(message)
        return self._trim_messages()

    def add_user_message(self, content):
        return self.add_message("user", content)

    def add_ai_message(self, content):
        return self.add_message("assistant", content)

    def get_messages(self):
        return self.messages

    def clear(self):
        self.messages.clear()

    def _trim_messages(self):
        if len(self.messages) > self.max_messages:
            return self.messages.pop(0)
        return None


class RoleMemoryManager:
    def __init__(self, max_messages=16):
        self.user_role_memories = {}
        self.long_term_candidates = {}
        self.loaded_session_ids = {}
        self.max_messages = max_messages
        self.summary_threshold = 8

    def get_memory_for_user_role(self, user_id, role_name):
        if user_id not in self.user_role_memories:
            self.user_role_memories[user_id] = {}
        if role_name not in self.user_role_memories[user_id]:
            self.user_role_memories[user_id][role_name] = ShortTermMemory(
                self.max_messages
            )
        return self.user_role_memories[user_id][role_name]

    def clear_memory_for_user_role(self, user_id, role_name):
        if (
            user_id in self.user_role_memories
            and role_name in self.user_role_memories[user_id]
        ):
            self.user_role_memories[user_id][role_name].clear()
        if (
            user_id in self.loaded_session_ids
            and role_name in self.loaded_session_ids[user_id]
        ):
            self.loaded_session_ids[user_id][role_name] = None

    def get_loaded_session_id(self, user_id, role_name):
        if (
            user_id in self.loaded_session_ids
            and role_name in self.loaded_session_ids[user_id]
        ):
            return self.loaded_session_ids[user_id][role_name]
        return None

    def set_loaded_session_id(self, user_id, role_name, session_id):
        if user_id not in self.loaded_session_ids:
            self.loaded_session_ids[user_id] = {}
        self.loaded_session_ids[user_id][role_name] = session_id

    def load_memory(self, user_id, role_name, session_id):
        db = SessionLocal()
        try:
            memory = self.get_memory_for_user_role(user_id, role_name)
            loaded_session_id = self.get_loaded_session_id(user_id, role_name)

            if loaded_session_id == session_id:
                return memory

            memory.clear()

            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id.desc())
                .limit(self.max_messages)
                .all()
            )
            messages.reverse()

            for message in messages:
                if message.role == "user":
                    memory.add_user_message(message.content)
                elif message.role == "assistant":
                    memory.add_ai_message(message.content)

            self.set_loaded_session_id(user_id, role_name, session_id)
            return memory
        finally:
            db.close()

    def collect_long_term_candidate(self, user_id, role_name, removed_message):
        if not removed_message:
            return None

        if user_id not in self.long_term_candidates:
            self.long_term_candidates[user_id] = {}
        if role_name not in self.long_term_candidates[user_id]:
            self.long_term_candidates[user_id][role_name] = []

        self.long_term_candidates[user_id][role_name].append(removed_message)
        return (
            len(self.long_term_candidates[user_id][role_name])
            >= self.summary_threshold
        )

    def pop_long_term_candidates(self, user_id, role_name):
        if (
            user_id in self.long_term_candidates
            and role_name in self.long_term_candidates[user_id]
        ):
            messages = self.long_term_candidates[user_id][role_name]
            self.long_term_candidates[user_id][role_name] = []
            return messages
        return []


class LongTermMemory:
    def __init__(self, max_messages=16):
        self.max_messages = max_messages
        self.summary_threshold = 8
        self.prompt = (
            "请总结以下对话，只保留对用户长期有价值、可稳定复用的信息。"
            "不要编造，不要加入当前一次性闲聊内容。\n\n"
        )

    def LongTermMemoryManager(self, user_id, role_name, session_id, candidate_message):
        message_text = "\n".join(
            [f"{item['role']}: {item['content']}" for item in candidate_message]
        )
        return ask_llm(self.prompt + message_text, [])

    def add_long_term_memory_to_db(self, user_id, role_name, session_id, summary):
        db = SessionLocal()
        try:
            db.add(
                Long_term_memory(
                    user_id=user_id,
                    role_name=role_name,
                    session_id=session_id,
                    summary=summary,
                )
            )
            db.commit()
        finally:
            db.close()

    def load_long_term_memory(self, user_id, role_name, limit=3):
        db = SessionLocal()
        try:
            long_term_memory = (
                db.query(Long_term_memory)
                .filter(
                    Long_term_memory.user_id == user_id,
                    Long_term_memory.role_name == role_name,
                )
                .order_by(Long_term_memory.id.desc())
                .limit(limit)
                .all()
            )
            long_term_memory.reverse()
            return [message.summary for message in long_term_memory]
        finally:
            db.close()

    def build_long_term_history(self, user_id, role_name, limit=3):
        summaries = self.load_long_term_memory(user_id, role_name, limit)

        history = []
        for summary in summaries:
            history.append(
                {
                    "role": "assistant",
                    "content": (
                        "以下是已知长期记忆摘要，仅在与当前问题直接相关时参考，"
                        f"不确定时不要强答：{summary}"
                    ),
                }
            )

        return history
