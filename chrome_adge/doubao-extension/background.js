function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTabComplete(tabId, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === "complete") return;
    await sleep(500);
  }
  throw new Error("Timed out waiting for page load.");
}

async function extractFromTab(tabId) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: async () => {
      function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
      }

      function normalizeText(text) {
        return String(text || "")
          .replace(/\u00a0/g, " ")
          .replace(/\r\n/g, "\n")
          .replace(/\n{3,}/g, "\n\n")
          .trim();
      }

      function combineTextParts(parts) {
        return parts.map(normalizeText).filter(Boolean).join("\n");
      }

      async function autoScroll() {
        for (let i = 0; i < 8; i += 1) {
          window.scrollTo(0, document.body.scrollHeight);
          await sleep(700);
        }
        for (let i = 0; i < 8; i += 1) {
          window.scrollTo(0, 0);
          await sleep(700);
        }
      }

      function roleHintFromMeta(meta) {
        const hint = [
          meta.className,
          meta.domRole,
          meta.dataTestid,
          meta.ariaLabel,
          meta.text.slice(0, 120),
        ]
          .join(" ")
          .toLowerCase();

        if (
          /\buser\b/.test(hint) ||
          /\bhuman\b/.test(hint) ||
          /\bme\b/.test(hint) ||
          /justify-end/.test(hint) ||
          /self-end/.test(hint) ||
          /items-end/.test(hint) ||
          /ml-auto/.test(hint) ||
          /text-right/.test(hint) ||
          /flex-row-reverse/.test(hint)
        ) {
          return "user";
        }

        if (
          /\bassistant\b/.test(hint) ||
          /\bagent\b/.test(hint) ||
          /\bbot\b/.test(hint) ||
          /\bai\b/.test(hint) ||
          /\bmodel\b/.test(hint) ||
          /justify-start/.test(hint) ||
          /self-start/.test(hint) ||
          /items-start/.test(hint) ||
          /mr-auto/.test(hint) ||
          /text-left/.test(hint)
        ) {
          return "assistant";
        }

        return null;
      }

      function inferRoles(messages) {
        let lastRole = null;
        return messages.map((message, index) => {
          const hinted = roleHintFromMeta(message);
          let role = hinted;

          if (!role) {
            role = index === 0 ? "user" : lastRole === "user" ? "assistant" : "user";
          }

          lastRole = role;
          return {
            ...message,
            domRole: message.domRole || "",
            role,
            speaker: role === "assistant" ? "agent" : "user",
          };
        });
      }

      function buildTurns(messages) {
        const turns = [];

        for (const message of messages) {
          const content = normalizeText(message.text);
          if (!content) continue;

          const current = turns[turns.length - 1];
          if (current && current.role === message.role) {
            current.content = combineTextParts([current.content, content]);
            current.messageCount += 1;
            current.messageIndexes.push(message.index);
            continue;
          }

          turns.push({
            role: message.role,
            speaker: message.speaker,
            content,
            messageCount: 1,
            messageIndexes: [message.index],
          });
        }

        return turns;
      }

      function buildTranscript(turns) {
        return turns
          .map((turn) => `${turn.speaker}:\n${turn.content}`)
          .join("\n\n");
      }

      function buildHandoffPrompt(turns) {
        const transcript = buildTranscript(turns);
        return [
          "你是一个对话流接力智能体。",
          "下面的历史对话中，`user` 表示用户，`assistant` 表示你自己。",
          "你需要继续扮演 `assistant` 这个角色，基于历史对话继续任务，不要重复已经确认过的内容。",
          "如果历史里有未完成事项，请优先接着处理。",
          "",
          "历史对话：",
          transcript,
        ].join("\n");
      }

      function collectMessages() {
        const selectors = [
          "[class*='message-item']",
          "[data-testid*='message']",
          "[data-message]",
          "[role='article']",
          "[class*='chat-message']",
          "article",
        ];

        const selector = selectors.join(",");
        const candidates = Array.from(document.querySelectorAll(selector));

        const nodes = candidates.filter((node) => {
          return !candidates.some((other) => other !== node && node.contains(other));
        });

        const messages = [];
        for (const node of nodes) {
          const text = normalizeText(node.innerText);
          if (!text || text.length < 2) continue;
          messages.push({
            text,
            tag: node.tagName,
            className: node.className || "",
            domRole: node.getAttribute("role") || "",
            dataTestid: node.getAttribute("data-testid") || "",
            ariaLabel: node.getAttribute("aria-label") || "",
            index: messages.length,
          });
        }

        return messages;
      }

      await autoScroll();

      let messages = collectMessages();
      if (!messages.length) {
        messages = [
          {
            text: normalizeText(document.body.innerText || ""),
            tag: "BODY",
            className: "",
            domRole: "",
            dataTestid: "",
            ariaLabel: "",
            index: 0,
          },
        ].filter((item) => item.text);
      }

      const inferredMessages = inferRoles(messages);
      const turns = buildTurns(inferredMessages);
      const transcriptText = buildTranscript(turns);
      const handoffPrompt = buildHandoffPrompt(turns);

      return {
        source: "doubao",
        url: location.href,
        title: document.title,
        capturedAt: new Date().toISOString(),
        messageCount: inferredMessages.length,
        turnCount: turns.length,
        messages: inferredMessages,
        turns,
        transcriptText,
        handoffPrompt,
      };
    },
  });

  return result.result;
}

async function openTabAndExtract(url) {
  const tab = await chrome.tabs.create({ url, active: true });
  await waitForTabComplete(tab.id);
  await sleep(1500);
  return extractFromTab(tab.id);
}

async function extractCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab found.");
  if (!tab.url?.startsWith("https://www.doubao.com/")) {
    throw new Error("Please open a Doubao thread tab first.");
  }
  await waitForTabComplete(tab.id);
  await sleep(1500);
  return extractFromTab(tab.id);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      if (message?.type === "EXPORT_URL") {
        const data = await openTabAndExtract(message.url);
        sendResponse({
          ok: true,
          data,
          filename: message.filename || "doubao-thread.json",
          status: `Extracted ${data.messageCount || 0} messages and ${data.turnCount || 0} turns.`,
        });
        return;
      }

      if (message?.type === "EXPORT_CURRENT") {
        const data = await extractCurrentTab();
        sendResponse({
          ok: true,
          data,
          filename: message.filename || "doubao-thread.json",
          status: `Extracted ${data.messageCount || 0} messages and ${data.turnCount || 0} turns.`,
        });
        return;
      }

      sendResponse({ ok: false, error: "Unknown message type." });
    } catch (err) {
      sendResponse({ ok: false, error: String(err?.message || err) });
    }
  })();

  return true;
});
