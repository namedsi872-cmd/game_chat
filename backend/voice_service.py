#旧版（弃）
import os

from faster_whisper import WhisperModel

model = None
model_name = os.getenv(
    "VOICE2TEXT_MODEL",
    r"C:\Users\Zephy\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120",
)

def get_model():
    global model
    if model is None:
        model = WhisperModel(model_name, device="cpu", compute_type="int8", local_files_only=True)
    return model

def transcribe_audio(file_path: str) -> str:
    model = get_model()
    segments, info = model.transcribe(file_path, language="zh")
    text = "".join([segment.text for segment in segments])
    return text.strip()
