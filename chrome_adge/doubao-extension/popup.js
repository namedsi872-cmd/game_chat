const threadUrl = document.getElementById("threadUrl");
const fileName = document.getElementById("fileName");
const fileExt = document.getElementById("fileExt");
const outputMode = document.getElementById("outputMode");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const exportUrlBtn = document.getElementById("exportUrl");
const exportCurrentBtn = document.getElementById("exportCurrent");
let lastDownloadId = null;
let lastSavedPath = "";
let fileLocationBtn = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function setPreview(text) {
  if (!text) {
    previewEl.style.display = "none";
    previewEl.textContent = "";
    return;
  }
  previewEl.style.display = "block";
  previewEl.textContent = text;
}

function getModeExtension(mode) {
  if (mode === "flow-json") return ".flow.json";
  return ".handoff.txt";
}

function stripKnownExtensions(name) {
  return String(name || "")
    .trim()
    .replace(/\.flow\.json$/i, "")
    .replace(/\.handoff\.txt$/i, "")
    .replace(/\.transcript\.txt$/i, "")
    .replace(/\.json$/i, "")
    .replace(/\.txt$/i, "");
}

function syncExtensionLabel() {
  fileExt.textContent = getModeExtension(outputMode.value);
}

function buildSaveTarget(filename, mode) {
  const stem = stripKnownExtensions(filename) || "doubao-thread";
  return `${stem}${getModeExtension(mode)}`;
}

function pathExt(filename) {
  const match = String(filename || "").match(/(\.[a-z0-9]+)$/i);
  return match ? match[1].toLowerCase() : ".txt";
}

function buildBlobByMode(response, mode) {
  if (mode === "flow-json") {
    const text = JSON.stringify(response.data, null, 2);
    return new Blob([text], { type: "application/json;charset=utf-8" });
  }

  const text = response.data?.handoffPrompt || "";
  return new Blob([text], { type: "text/plain;charset=utf-8" });
}

async function waitForDownloadComplete(downloadId, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const items = await chrome.downloads.search({ id: downloadId });
    const item = items && items[0];
    if (item) {
      if (item.state === "complete") return item;
      if (item.state === "interrupted") {
        throw new Error(item.error || "Download interrupted.");
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error("Timed out waiting for file save.");
}

function renderSavedPath(path) {
  if (!path) return;
  setStatus(`Saved to: ${path}`);
  if (!fileLocationBtn) {
    fileLocationBtn = document.createElement("button");
    fileLocationBtn.type = "button";
    fileLocationBtn.className = "secondary";
    fileLocationBtn.textContent = "打开文件所在位置";
    fileLocationBtn.style.marginTop = "8px";
    fileLocationBtn.addEventListener("click", async () => {
      if (lastDownloadId == null) return;
      await chrome.downloads.show(lastDownloadId);
    });
    statusEl.insertAdjacentElement("afterend", fileLocationBtn);
  }
  fileLocationBtn.style.display = "block";
}

async function doExport(message, filename, mode) {
  setStatus("Working...");
  try {
    const saveTarget = buildSaveTarget(filename, mode);
    const response = await chrome.runtime.sendMessage(message);
    if (!response?.ok) {
      setStatus(response?.error || "Export failed.");
      return;
    }

    setStatus(response.status || "Extracted. Saving...");
    const blob = buildBlobByMode(response, mode);
    const objectUrl = URL.createObjectURL(blob);
    try {
      lastDownloadId = await chrome.downloads.download({
        url: objectUrl,
        filename: saveTarget,
        saveAs: true,
      });
    } finally {
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    }

    const item = await waitForDownloadComplete(lastDownloadId);
    lastSavedPath = item.filename || saveTarget;
    setPreview(response.data?.handoffPrompt || JSON.stringify(response.data?.turns || [], null, 2));
    renderSavedPath(lastSavedPath);
  } catch (err) {
    setStatus(String(err?.message || err));
  }
}

outputMode.addEventListener("change", () => {
  syncExtensionLabel();
  setStatus("准备就绪。");
  if (fileLocationBtn) {
    fileLocationBtn.style.display = "none";
  }
  lastDownloadId = null;
  lastSavedPath = "";
});

exportUrlBtn.addEventListener("click", async () => {
  const url = threadUrl.value.trim();
  const filename = fileName.value.trim() || "doubao-thread";
  const mode = outputMode.value;
  if (!url) {
    setStatus("Please paste a Doubao thread URL first.");
    return;
  }
  await doExport({ type: "EXPORT_URL", url, filename, mode }, filename, mode);
});

exportCurrentBtn.addEventListener("click", async () => {
  const filename = fileName.value.trim() || "doubao-thread";
  const mode = outputMode.value;
  await doExport({ type: "EXPORT_CURRENT", filename, mode }, filename, mode);
});

syncExtensionLabel();
