$ErrorActionPreference = "Stop"

# Default to the DeepSeek OpenAI-compatible backend.
$env:GROQ_PROXY_PROVIDER = "openai"
$env:GROQ_PROXY_UPSTREAM_URL = "https://api.deepseek.com"
$env:GROQ_PROXY_UPSTREAM_MODEL = "deepseek-v4-pro"
$env:GROQ_PROXY_PUBLIC_MODEL = "openai/gpt-oss-120b:free"
$env:VOICE2TEXT_MODEL = "C:\Users\Zephy\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120"
$env:HF_HUB_OFFLINE = "1"

python "$PSScriptRoot\groq_compat_proxy.py" --host 127.0.0.1 --port 800
