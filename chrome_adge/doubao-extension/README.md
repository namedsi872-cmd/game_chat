# Doubao Thread Exporter

Load this folder as an unpacked Chrome or Edge extension.

## What it does

- Opens a Doubao thread URL in your logged-in browser session.
- Extracts the thread into JSON.
- Infers `user` / `assistant` roles from the page layout.
- Builds a `turns` array and a `transcriptText` field in `user:` / `agent:` format.
- Generates a `handoffPrompt` for downstream agents.
- Lets you save the result to `D:` or any folder you choose.

## Output modes

- `对话流 JSON`
  - Saves the structured flow package.
  - Output filename becomes `*.flow.json`.
- `接力 TXT`
  - Saves a plain text prompt that can be handed to another agent directly.
  - Output filename becomes `*.handoff.txt`.

## File naming

- The file name input only edits the base name.
- The extension is shown next to it and changes with the output mode.
- `接力 TXT` uses `.handoff.txt`.
- `对话流 JSON` uses `.flow.json`.

## How to use

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer mode.
3. Click `Load unpacked` and select this `doubao-extension` folder.
4. Open the extension popup.
5. Paste a Doubao thread URL.
6. Choose an output mode.
7. Click `打开并导出`.
8. When the save dialog appears, choose a location on `D:`.

## If `role` was empty before

The earlier version only read the DOM `role` attribute. Doubao does not always set that attribute on message nodes, so the field came out empty.

The current version infers role from:

- class names like `justify-end`, `message-item`, `assistant`, `bot`
- alignment hints in the DOM
- message order as a fallback

## Existing JSON files

If you already exported an older JSON file, run the standalone transformer:

```bash
node doubao_flow_transform.mjs "D:\doubao-thread.json"
```

It will create:

- `D:\doubao-thread.flow.json`
- `D:\doubao-thread.handoff.txt`

## Notes

- The extraction logic is heuristic. If Doubao changes its DOM, the selector list may need adjustment.
- If you want, this can be extended further into a more complete handoff agent with summarization and memory.
