import json
import queue

from dashscope.audio.asr import RecognitionCallback


class AsrCallback(RecognitionCallback):
    def __init__(self, result_queue: queue.Queue):
        super().__init__()
        self.result_queue = result_queue

    def on_open(self):
        print("ASR WebSocket connected")

    def on_close(self):
        print("ASR WebSocket closed")

    def on_complete(self):
        print("ASR recognition complete")

    def on_error(self, message):
        print("ASR error:", message)

    def on_event(self, result):
        print("ASR event received:", type(result).__name__)

        text = ""
        sentence_end = False
        request_id = None
        usage = None

        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"raw_text": result}

        if hasattr(result, "get_sentence"):
            sentence = result.get_sentence() or {}
            text = sentence.get("text", "") or ""
            sentence_end = bool(sentence.get("sentence_end"))
            request_id = getattr(result, "get_request_id", lambda: None)()
            usage = getattr(result, "get_usage", lambda _sentence: None)(sentence)
            payload = {
                "type": "result",
                "text": text,
                "sentence_end": sentence_end,
                "request_id": request_id,
                "usage": usage,
                "sentence": sentence,
            }
        elif isinstance(result, dict):
            sentence = result.get("output", {}).get("sentence", {})
            text = sentence.get("text", result.get("raw_text", "")) or ""
            sentence_end = bool(sentence.get("sentence_end"))
            request_id = result.get("request_id")
            usage = result.get("usage")
            payload = {
                "type": "result",
                "text": text,
                "sentence_end": sentence_end,
                "request_id": request_id,
                "usage": usage,
                "sentence": sentence,
            }
        else:
            payload = {
                "type": "result",
                "text": str(result),
                "sentence_end": False,
                "request_id": None,
                "usage": None,
                "sentence": {},
            }

        self.result_queue.put(payload)
