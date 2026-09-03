# Groq-compatible local proxy

This proxy lets a Groq-style client talk to DeepSeek's OpenAI-compatible API.

## Start

```powershell
cd F:\great\hardwork\ionic_agent\game_chat
.\run_groq_compat_proxy.ps1
```

The proxy listens on:

```text
http://127.0.0.1:800
```

## Default setup

The PowerShell launcher is prefilled for the DeepSeek API:

```text
provider: openai
upstream_url: https://api.deepseek.com
upstream_model: deepseek-v4-pro
```

The mod config already has `useNativeTts = true`, so Groq TTS is bypassed.
The proxy reads `apiKey` from `verity-common.toml` by default.

If your DeepSeek model name is different, edit:

```powershell
$env:GROQ_PROXY_UPSTREAM_MODEL = "your-model-name"
```

## If your backend is different

Set:

```powershell
$env:GROQ_PROXY_PROVIDER = "openai"
$env:GROQ_PROXY_UPSTREAM_URL = "https://api.deepseek.com"
```

## Client URL

The proxy accepts both:

- `http://127.0.0.1:800/v1`
- `http://127.0.0.1:800/openai/v1`

Use the one your client allows you to configure.

## Notes

- `GET /v1/models` returns a single fake Groq-style model list.
- `POST /v1/chat/completions` and `POST /openai/v1/chat/completions` are supported.
- Streaming is supported for OpenAI-compatible upstreams.
