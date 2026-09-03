import os
import tempfile
import asyncio
import json
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import SessionLocal
from backend.models import ChatMessage, ChatSession, User
from backend.tts_service import TtsRealtimeService
from backend.voice_service import get_model, transcribe_audio
from backend.voice_input.asr_service import AsrService
from config import DEFAULT_ROLE
from llm import ask_llm,ask_llm_stream
from role_loader import (
    all_role_name,
    get_game_aliases,
    get_role_prompt,
    normalize_game_name,
    normalize_role_name,
)
from shared_managers import long_term_memory_manager, role_memory_manager
from tools.import_history_tool import import_external_chat_history
from workflow.agent_graph import graph
from workflow.training_flow import (
    apply_game_context_prompt,
    handle_training_flow,
    handle_training_flow_stream,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

all_role_names = all_role_name()


def normalize_session_game_name(game_name: Optional[str]) -> Optional[str]:
    return normalize_game_name(game_name)


def find_latest_session_by_user_role_game(db, user_id: int, role_name: str, game_name: Optional[str]):
    normalized_game_name = normalize_session_game_name(game_name)

    query = db.query(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatSession.role_name == role_name,
    )

    if normalized_game_name is None:
        query = query.filter(ChatSession.game_name.is_(None))
    else:
        query = query.filter(ChatSession.game_name.in_(get_game_aliases(normalized_game_name)))

    chat_session = query.order_by(ChatSession.id.desc()).first()

    if chat_session and chat_session.game_name != normalized_game_name:
        chat_session.game_name = normalized_game_name
        db.commit()
        db.refresh(chat_session)

    return chat_session


class RegisterRequest(BaseModel):
    username: str
    password: str


class MemoryRequest(BaseModel):
    user_id: int
    message: str
    role_name: str = DEFAULT_ROLE
    session_id: Optional[int] = Field(default=None, example=None)
    raw_json_text: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "message": "你好",
                "role_name": "yagami_light",
                "session_id": None,
                "raw_json_text": None,
            }
        }


class ChangeRoleRequest(BaseModel):
    user_id: int
    role_name: str
    game_name: Optional[str] = None


class NewSessionRequest(BaseModel):
    user_id: int
    role_name: str = DEFAULT_ROLE
    game_name: Optional[str] = None
    title: Optional[str] = None


class ClearMemoryRequest(BaseModel):
    user_id: int
    role_name: str = DEFAULT_ROLE


@app.get("/health")
def health():
    return {"message": "service ok"}


@app.post("/register")
async def register(data: RegisterRequest):
    db = SessionLocal()
    try:
        user = User(username=data.username, password_hash=data.password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"message": "用户注册成功"}
    finally:
        db.close()


@app.post("/login")
async def login(data: RegisterRequest):
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(
                User.username == data.username,
                User.password_hash == data.password,
            )
            .first()
        )
        if user:
            return {"message": "登录成功", "user_id": user.id}
        return {"message": "用户名或密码错误"}, 401
    finally:
        db.close()


@app.post("/change_role")
async def change_role(data: ChangeRoleRequest):
    db = SessionLocal()
    try:
        user_id = data.user_id
        role_name = data.role_name
        game_name = normalize_session_game_name(data.game_name)

        chat_session = find_latest_session_by_user_role_game(
            db,
            user_id,
            role_name,
            game_name,
        )

        if not chat_session:
            chat_session = ChatSession(
                user_id=user_id,
                role_name=role_name,
                game_name=game_name,
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)

        return {
            "user_id": user_id,
            "role_name": role_name,
            "session_id": chat_session.id,
            "game_name": chat_session.game_name,
        }
    finally:
        db.close()


@app.post("/chat")
async def chat(request: Request, data: MemoryRequest):
    db = SessionLocal()
    streaming_response = False
    request_started_at = time.perf_counter()

    try:
        user_id = data.user_id
        session_id = data.session_id
        role_name = data.role_name
        message = (data.message or "").strip()

        if not user_id:
            return {"error": "请先登录"}, 400

        # 有外部 json 文件时，优先走导入逻辑，不要求普通 message
        if data.raw_json_text:
            result = import_external_chat_history.invoke({
                "user_id": user_id,
                "role_name": role_name,
                "raw_json_text": data.raw_json_text,
            })

            if not result.get("ok"):
                return {"error": result.get("message", "导入失败")}

            return {
                "message": result["message"],
                "reply": (
                    f"{result['message']}，"
                    f"共导入 {result['imported_count']} 条消息。"
                ),
                "session_id": result["session_id"],
                "imported_count": result["imported_count"],
                "title": result["title"],
            }

        if not message:
            return {"error": "message不能为空"}

        if session_id == 0:
            return {
                "error": "session_id 不能为 0。新会话请传 null，继续会话请传已有 session_id"
            }

        session_lookup_started_at = time.perf_counter()
        chat_session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            .first()
        )
        session_lookup_elapsed = time.perf_counter() - session_lookup_started_at

        if not chat_session:
            return {"error": "session不存在，或不属于当前用户"}

        current_prompt = get_role_prompt(role_name)
        initial_state = {
            "user_id": user_id,
            "role_name": role_name,
            "session_id": session_id,
            "game_name": chat_session.game_name,
            "message": message,
            "intent": "",
            "intent_reason": "",
            "now_mode": chat_session.active_mode if chat_session.active_mode else "",
            "final_mode": "",
            "full_history": [],
        }

        graph_started_at = time.perf_counter()
        graph_result = graph.invoke(initial_state)
        graph_elapsed = time.perf_counter() - graph_started_at
        final_mode = graph_result["final_mode"]
        full_history = graph_result["full_history"]
        current_history = full_history + [
            {
                "role": "user",
                "content": message,
            }
        ]

        chat_session.active_mode = final_mode
        chat_session.active_mode_updated_at = datetime.now()

        role_memory = role_memory_manager.get_memory_for_user_role(user_id, role_name)
        removed_user_message = role_memory.add_user_message(message)

        if final_mode == "training":
            reply_chunks = handle_training_flow_stream(
                message,
                current_prompt,
                current_history,
                game_name=chat_session.game_name,
            )
        elif final_mode == "review":
            reply_chunks = handle_training_flow_stream(
                message,
                current_prompt,
                current_history,
                game_name=chat_session.game_name,
            )
        elif final_mode == "draw":
            reply_chunks = iter(["绘图模式暂未完成。"])
        elif chat_session.game_name:
            current_prompt = apply_game_context_prompt(
                current_prompt,
                game_name=chat_session.game_name,
            )
            reply_chunks = ask_llm_stream(
                current_prompt,
                current_history,
            )
        else:
            reply_chunks = ask_llm_stream(
                current_prompt,
                current_history,
            )


        def stream_reply():
            reply_parts = []
            first_chunk_logged = False

            try:
                for chunk in reply_chunks:
                    if not chunk:
                        continue

                    if not first_chunk_logged:
                        first_chunk_logged = True
                        first_chunk_elapsed = time.perf_counter() - request_started_at
                        print(
                            "[chat_timing] "
                            f"session={session_id} "
                            f"mode={final_mode} "
                            f"session_lookup={session_lookup_elapsed:.3f}s "
                            f"graph={graph_elapsed:.3f}s "
                            f"first_chunk={first_chunk_elapsed:.3f}s"
                        )

                    reply_parts.append(chunk)
                    yield chunk

                reply = "".join(reply_parts).strip()
                
                removed_ai_message = role_memory.add_ai_message(reply)

                should_summarize = False

                if removed_user_message:
                    if role_memory_manager.collect_long_term_candidate(
                        user_id, role_name, removed_user_message
                    ):
                        should_summarize = True

                if removed_ai_message:
                    if role_memory_manager.collect_long_term_candidate(
                        user_id, role_name, removed_ai_message
                    ):
                        should_summarize = True

                if should_summarize:
                    message_list = role_memory_manager.pop_long_term_candidates(
                        user_id, role_name
                    )
                    reply_memory = long_term_memory_manager.LongTermMemoryManager(
                        user_id, role_name, session_id, message_list
                    )
                    long_term_memory_manager.add_long_term_memory_to_db(
                        user_id, role_name, session_id, reply_memory
                    )

                db.add(ChatMessage(session_id=session_id, role="user", content=message))
                db.add(ChatMessage(session_id=session_id, role="assistant", content=reply))
                db.commit()
                total_elapsed = time.perf_counter() - request_started_at
                print(
                    "[chat_timing] "
                    f"session={session_id} "
                    f"mode={final_mode} "
                    f"total={total_elapsed:.3f}s"
                )
            finally:
                db.close()

        streaming_response = True

        return StreamingResponse(
            stream_reply(),
            media_type="text/plain; charset=utf-8",
            headers={
                "X-Session-Id": str(session_id),
            },
        )
    finally:
        if not streaming_response:
            db.close()


@app.get("/role_names")
def role_names():
    return {"role_names": all_role_names}


@app.post("/sessions/new")
async def create_new_session(data: NewSessionRequest):
    db = SessionLocal()
    try:
        if not data.user_id:
            return {"error": "请先登录"}

        game_name = normalize_session_game_name(data.game_name)
        chat_session = ChatSession(
            user_id=data.user_id,
            role_name=data.role_name,
            title=data.title,
            game_name=game_name,
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        return {
            "message": "新会话创建成功",
            "user_id": data.user_id,
            "role_name": data.role_name,
            "session_id": chat_session.id,
            "title": chat_session.title,
            "game_name": chat_session.game_name,
        }
    finally:
        db.close()


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: int):
    db = SessionLocal()
    try:
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )

        return {
            "game_name": normalize_session_game_name(chat_session.game_name) if chat_session else None,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                }
                for message in messages
            ]
        }
    finally:
        db.close()


@app.get("/sessions/list/{user_id}/{role_name}")
async def get_sessions(user_id: int, role_name: str, game_name: Optional[str] = None):
    db = SessionLocal()
    try:
        normalized_game_name = normalize_session_game_name(game_name)
        query = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.role_name == role_name,
        )

        if normalized_game_name is None:
            query = query.filter(ChatSession.game_name.is_(None))
        else:
            query = query.filter(ChatSession.game_name.in_(get_game_aliases(normalized_game_name)))

        sessions = query.order_by(ChatSession.id.desc()).all()

        return {
            "sessions": [
                {
                    "id": session.id,
                    "title": session.title,
                    "game_name": normalize_session_game_name(session.game_name),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
                for session in sessions
            ]
        }
    finally:
        db.close()


@app.on_event("startup")
def preload_voice_model():
    get_model()


@app.post("/voice/asr")
async def voice_asr(file: UploadFile = File(...)):
    content = await file.read()
    suffix = os.path.splitext(file.filename)[1] or ".webm"
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        text = transcribe_audio(temp_file_path)
        return {"text": text}
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.websocket("/voice/asr/ws")
async def voice_asr_ws(websocket: WebSocket):
    await websocket.accept()
    asr_service = AsrService()
    is_started = False

    async def forward_results():
        while True:
            result = await asyncio.to_thread(asr_service.get_result, 0.1)
            if result is None:
                if not is_started:
                    await asyncio.sleep(0.01)
                continue

            await websocket.send_json(result)

    result_task = asyncio.create_task(forward_results())

    try:
        while True:
            incoming = await websocket.receive()

            if incoming["type"] == "websocket.disconnect":
                break

            audio_bytes = incoming.get("bytes")
            if audio_bytes is not None:
                if not is_started:
                    await asyncio.to_thread(asr_service.start)
                    is_started = True

                await asyncio.to_thread(
                    asr_service.send_audio_frame,
                    audio_bytes,
                )
                continue

            raw_text = incoming.get("text")
            if not raw_text:
                continue

            data = json.loads(raw_text)
            message_type = data.get("type")

            if message_type == "start":
                if not is_started:
                    await asyncio.to_thread(asr_service.start)
                    is_started = True

                await websocket.send_json({"type": "started"})

            elif message_type == "stop":
                if is_started:
                    await asyncio.to_thread(asr_service.stop)
                    is_started = False

                await websocket.send_json({"type": "stopped"})

            elif message_type == "finish":
                break

    except WebSocketDisconnect:
        print("ASR websocket disconnected")
    except Exception as exc:
        await websocket.send_json({
            "type": "error",
            "message": str(exc),
        })
    finally:
        is_started = False
        result_task.cancel()
        try:
            await result_task
        except asyncio.CancelledError:
            pass


@app.websocket("/voice/tts/ws")
async def voice_tts_ws(websocket: WebSocket):
    await websocket.accept()
    tts_service = TtsRealtimeService()

    try:
        await asyncio.to_thread(tts_service.connect)
        await asyncio.to_thread(tts_service.start_session)

        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            message_type = data.get("type")

            if message_type == "append_text":
                text = data.get("text", "")
                if text.strip():
                    await asyncio.to_thread(tts_service.append_text, text)

            elif message_type == "set_role":
                role_name = data.get("role_name")
                await asyncio.to_thread(tts_service.update_role, role_name)

            elif message_type == "commit":
                await asyncio.to_thread(tts_service.start_commit)

                while True:
                    if not tts_service.audio_queue.empty():
                        audio_chunk = tts_service.audio_queue.get()
                        await websocket.send_bytes(audio_chunk)
                        continue

                    if tts_service.is_response_done():
                        break

                    await asyncio.sleep(0.01)

            elif message_type == "finish":
                await asyncio.to_thread(tts_service.finish)
                break

    except WebSocketDisconnect:
        print("TTS websocket disconnected")

    finally:
        await asyncio.to_thread(tts_service.close)


@app.post("/clear_memory")
async def clear_memory(data: ClearMemoryRequest):
    if not data.user_id:
        return {"error": "请先登录"}, 400

    role_memory_manager.clear_memory_for_user_role(data.user_id, data.role_name)

    return {
        "message": "历史记录已清除",
        "role_name": data.role_name,
        "user_id": data.user_id,
    }


@app.get("/memory/{user_id}/{role_name}")
async def get_memory(user_id: int, role_name: str):
    role_name = normalize_role_name(role_name)
    role_memory = role_memory_manager.get_memory_for_user_role(user_id, role_name)
    return {"messages": role_memory.get_messages()}


@app.get("/long_term_memory/{user_id}/{role_name}")
async def get_long_term_memory(user_id: int, role_name: str):
    role_name = normalize_role_name(role_name)
    long_term_memory = long_term_memory_manager.load_long_term_memory(
        user_id, role_name, limit=3
    )
    return {"summary": long_term_memory}


@app.get("/records/{user_id}")
async def get_records(user_id: int, page: int = 1, page_size: int = 5):
    db = SessionLocal()
    try:
        page = max(page, 1)
        page_size = max(page_size, 1)
        offset = (page - 1) * page_size

        total = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).count()

        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        records = []
        for session in sessions:
            last_message = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.id.desc())
                .first()
            )

            records.append({
                "session_id": session.id,
                "title": session.title or f"会话 {session.id}",
                "role_name": session.role_name,
                "game_name": normalize_session_game_name(session.game_name),
                "updated_at": session.updated_at,
                "last_message": last_message.content if last_message else "",
            })

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "records": records,
        }
    finally:
        db.close()
