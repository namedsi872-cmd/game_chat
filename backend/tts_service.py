import os
import queue
import threading
import base64
import dashscope

from dotenv import load_dotenv
from dashscope.audio.qwen_tts_realtime import (
    AudioFormat,
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
)

load_dotenv()

ROLE_TTS_CONFIG = {
    "yagami_light": {
        "voice": "Moon",
        "instructions": "请用年轻、冷静、克制、偏冷感的男声说话。语速略慢，情绪起伏很小，减少热情感，减少明亮笑意，声音不要显老，整体更理性、更疏离。",
    },
    "mihaisha": {
        "voice": "Cherry",
        "instructions": "请用活泼、甜美、轻快、元气感明显的少女音说话，语气灵动自然，带一点俏皮感。",
    },
    "other_role": {
        "voice": "Serena",
        "instructions": "请用自然、温柔、有陪伴感的语气说话。",
    },
}


class TtsCallback(QwenTtsRealtimeCallback):
    def __init__(self, audio_queue: queue.Queue):
        super().__init__()
        self.audio_queue = audio_queue
        self.response_done_event = threading.Event()

    def on_open(self):
        print("TTS WebSocket connected")

    def on_close(self, close_status_code, close_msg):
        print("TTS WebSocket closed:", close_status_code, close_msg)

    def on_event(self, response):
        print("TTS event:", response)

        try:
            event_type = response["type"]

            if event_type == "response.audio.delta":
                recv_audio_b64 = response["delta"]
                audio_bytes = base64.b64decode(recv_audio_b64)
                self.audio_queue.put(audio_bytes)

            if event_type == "response.done":
                self.response_done_event.set()

            if event_type == "session.finished":
                self.response_done_event.set()

            if event_type == "error":
                self.response_done_event.set()

        except Exception as e:
            print("TTS event parse error:", e)
            self.response_done_event.set()

    # 鍗℃瀹屾垚淇″彿
    def on_error(self, message: str):
        print("TTS error:", message)
        self.response_done_event.set()

    def reset_event(self):
        self.response_done_event.clear()

    # 绛夊緟鏃堕棿
    def wait_for_response_done(self, timeout: float = 10.0):
        return self.response_done_event.wait(timeout=timeout)


class TtsRealtimeService:
    def __init__(self):
        self.api_key = os.getenv("voice_API_KEY")
        self.model = os.getenv(
            "TTS_REALTIME_MODEL",
            "qwen3-tts-instruct-flash-realtime"
        )
        self.voice = os.getenv("TTS_REALTIME_VOICE", "Serena")
        self.mode = os.getenv("TTS_REALTIME_MODE", "commit")
        self.instructions = os.getenv(
            "TTS_REALTIME_INSTRUCTIONS",
            "请用自然、温柔、有陪伴感的语气说话。"
        )

        self.audio_queue = queue.Queue()
        self.callback = TtsCallback(self.audio_queue)
        self.tts = None
        self.current_role_name = "other_role"

    def get_role_tts_config(self, role_name: str | None):
        if not role_name:
            return {
                "voice": self.voice,
                "instructions": self.instructions,
            }

        return ROLE_TTS_CONFIG.get(
            role_name,
            {
                "voice": self.voice,
                "instructions": self.instructions,
            },
        )

    def connect(self):
        if not self.api_key:
            raise ValueError("API key not configured")

        os.environ["voice_API_KEY"] = self.api_key
        dashscope.api_key = self.api_key

        self.tts = QwenTtsRealtime(
            model=self.model,
            callback=self.callback,
            url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        )

        self.tts.connect()

    def start_session(self):
        if not self.tts:
            raise ValueError("TTS connection has not been established")

        self.tts.update_session(
            voice=self.voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode=self.mode,
            instructions=self.instructions,
            optimize_instructions=True,
        )

    def update_role(self, role_name: str | None):
        if not self.tts:
            raise ValueError("TTS connection has not been established")

        self.current_role_name = role_name or "other_role"
        role_config = self.get_role_tts_config(role_name)
        self.voice = role_config["voice"]
        self.instructions = role_config["instructions"]
        self.start_session()

    def reconnect_with_current_role(self):
        self.close()
        self.connect()
        self.update_role(self.current_role_name)

    def append_text(self, text: str):
        if not self.tts:
            raise ValueError("TTS connection has not been established")

        if not text or not text.strip():
            return

        try:
            self.tts.append_text(text)
        except ConnectionError:
            self.reconnect_with_current_role()
            self.tts.append_text(text)

    def commit_text(self, timeout: float = 10.0):
        if not self.tts:
            raise ValueError("TTS connection has not been established")

        self.callback.reset_event()
        self.tts.commit()
        return self.callback.wait_for_response_done(timeout=timeout)

    def start_commit(self):
        if not self.tts:
            raise ValueError("TTS connection has not been established")

        try:
            self.callback.reset_event()
            self.tts.commit()
        except ConnectionError:
            self.reconnect_with_current_role()
            self.callback.reset_event()
            self.tts.commit()

    def is_response_done(self):
        return self.callback.response_done_event.is_set()

    def finish(self):
        if self.tts:
            self.tts.finish()

    def close(self):
        if self.tts:
            self.tts.close()
            self.tts = None
