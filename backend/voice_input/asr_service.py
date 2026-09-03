import os
import queue
from queue import Empty

import dashscope
from dashscope.audio.asr import Recognition

from backend.voice_input.asr_callback import AsrCallback


class AsrService:
    def __init__(self):
        self.api_key = os.getenv("voice_API_KEY")
        self.model = os.getenv("REALTIME_ASR_MODEL", "fun-asr-realtime")
        self.format = os.getenv("REALTIME_ASR_FORMAT", "pcm")
        self.sample_rate = int(os.getenv("REALTIME_ASR_SAMPLE_RATE", "16000"))

        self.result_queue = queue.Queue()
        self.callback = AsrCallback(self.result_queue)
        self.recognition = None

        dashscope.api_key = self.api_key

        self.workspace_id = os.getenv("DASHSCOPE_WORKSPACE_ID")
        self.ws_url = os.getenv("REALTIME_ASR_WS_URL")  # 鍒楄〃鍦板潃
        self.is_started = False

    def create_recognition(self):
        if self.ws_url:
            dashscope.base_websocket_api_url = self.ws_url
        elif self.workspace_id:
            dashscope.base_websocket_api_url = (
                f"wss://{self.workspace_id}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
            )

        self.recognition = Recognition(
            model=self.model,
            format=self.format,
            sample_rate=self.sample_rate,
            callback=self.callback,
        )

    def start(self):
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except Empty:
                break

        self.create_recognition()
        self.recognition.start()
        self.is_started = True

    def send_audio_frame(self, audio_bytes: bytes):
        if not self.recognition or not self.is_started:
            raise RuntimeError("ASR has not been started")
        self.recognition.send_audio_frame(audio_bytes)

    def stop(self):
        if not self.recognition or not self.is_started:
            return

        self.recognition.stop()
        self.is_started = False

    # 鍒楄〃缁撴灉
    def get_result(self, timeout: float = 0.1):
        try:
            return self.result_queue.get(timeout=timeout)
        except Empty:
            return None
