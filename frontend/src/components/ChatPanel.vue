<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import SessionHistory from '../components/SessionHistory.vue'
import VoiceInput from '../components/VoiceInput.vue'
import VoiceTTS from '../components/VoiceTTS.vue'

type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}
// 璇煶鎾姤
type VoiceTTSExpose = {
  connect: () => void
  enable: () => void
  disable: () => void
  appendTextChunk: (chunk: string) => void
  flushRemainingText: () => void
  close: () => void
}

type VoiceInputExpose = {
  startRecording: () => Promise<void>
  stopRecording: () => Promise<void>
}

declare global {
  interface Window {
    electronMiniWindow?: {
      resizeToContent: (payload: { width: number; height: number }) => void
    }
  }
}

const emit = defineEmits<{
  (e: 'go-home'): void
  (e: 'change-game', gameName: string): void
}>()

const props = defineProps({
  userId: {
    type: Number,
    default: null
  },
  roleName: {
    type: String,
    default: 'yagami_light'
  },
  gameName: {
    type: String,
    default: ''
  }
})

const isMiniMode = new URLSearchParams(window.location.search).get('mini') === '1'
const miniPanelExpanded = ref(false)
const miniTranscript = ref('')
const miniShellRef = ref<HTMLElement | null>(null)

const messageInputRef = ref<HTMLInputElement | null>(null)
const importFileInputRef = ref<HTMLInputElement | null>(null)
const replyContentRef = ref<HTMLElement | null>(null)
const isTyping = ref(false)
const voiceInputRef = ref<VoiceInputExpose | null>(null)
const voiceTtsRef = ref<VoiceTTSExpose | null>(null)

const sessionId = ref<number | null>(null)
const roleName = ref(props.roleName)
const gameName = ref(props.gameName)
const message = ref('')
const rawJsonText = ref('')
const selectedFileName = ref('')
const messages = ref<ChatMessage[]>([])
let miniResizeObserver: ResizeObserver | null = null
let miniResizeTimer: number | null = null

const getSessionStorageKey = () => {
  if (!props.userId) return ''
  return `chat_session_${props.userId}_${roleName.value}_${gameName.value || 'pure_chat'}`
}

const getStoredSessionId = () => {
  const storageKey = getSessionStorageKey()
  if (!storageKey) return null

  const rawValue = window.localStorage.getItem(storageKey)
  if (!rawValue) return null

  const parsedValue = Number(rawValue)
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null
}

const storeCurrentSessionId = (targetSessionId: number | null) => {
  const storageKey = getSessionStorageKey()
  if (!storageKey) return

  if (!targetSessionId) {
    window.localStorage.removeItem(storageKey)
    return
  }

  window.localStorage.setItem(storageKey, String(targetSessionId))
}

const syncMiniWindowSize = () => {
  if (!isMiniMode || !window.electronMiniWindow || !miniShellRef.value) return

  const rect = miniShellRef.value.getBoundingClientRect()
  const widthPadding = miniPanelExpanded.value ? 20 : 12
  const heightPadding = miniPanelExpanded.value ? 20 : 12
  const targetWidth = Math.ceil(rect.width + widthPadding)
  const targetHeight = Math.ceil(rect.height + heightPadding)

  window.electronMiniWindow.resizeToContent({
    width: targetWidth,
    height: targetHeight
  })
}

const queueMiniWindowResize = () => {
  if (!isMiniMode) return

  if (miniResizeTimer !== null) {
    window.clearTimeout(miniResizeTimer)
  }

  miniResizeTimer = window.setTimeout(() => {
    miniResizeTimer = null
    syncMiniWindowSize()
  }, 50)
}

const loadMessages = async (targetSessionId: number) => {
  const res = await fetch(`http://127.0.0.1:8000/sessions/${targetSessionId}/messages`)
  const data = await res.json()
  gameName.value = data.game_name || ''
  emit('change-game', gameName.value)
  messages.value = data.messages || []
}

const scrollToBottom = async () => {
  await nextTick()
  if (!replyContentRef.value) return
  replyContentRef.value.scrollTop = replyContentRef.value.scrollHeight
}

const handleSelectSession = async (targetSessionId: number) => {
  sessionId.value = targetSessionId
  storeCurrentSessionId(targetSessionId)
  await loadMessages(targetSessionId)
  await scrollToBottom()
}

const changeRole = async () => {
  const res = await fetch('http://127.0.0.1:8000/change_role', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: props.userId,
      role_name: roleName.value,
      game_name: gameName.value || null
    })
  })

  const data = await res.json()
  const latestSessionId = data.session_id
  gameName.value = data.game_name || ''
  emit('change-game', gameName.value)

  const storedSessionId = getStoredSessionId()
  sessionId.value = storedSessionId || latestSessionId

  if (sessionId.value) {
    await loadMessages(sessionId.value)
    storeCurrentSessionId(sessionId.value)
    await scrollToBottom()
  }
}

const createNewSession = async () => {
  const res = await fetch('http://127.0.0.1:8000/sessions/new', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: props.userId,
      role_name: roleName.value,
      game_name: gameName.value || null,
      title: null
    })
  })

  const data = await res.json()
  sessionId.value = data.session_id
  gameName.value = data.game_name || ''
  emit('change-game', gameName.value)
  storeCurrentSessionId(sessionId.value)
  message.value = ''
  rawJsonText.value = ''
  selectedFileName.value = ''
  miniTranscript.value = ''
  messages.value = []
}

const changeGame = async () => {
  emit('change-game', gameName.value)
  await changeRole()
}

const openImportFilePicker = () => {
  importFileInputRef.value?.click()
}

const clearImportedFile = () => {
  rawJsonText.value = ''
  selectedFileName.value = ''
  if (importFileInputRef.value) {
    importFileInputRef.value.value = ''
  }
}

const handleImportFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) return

  rawJsonText.value = await file.text()
  selectedFileName.value = file.name
}

const toggleMiniPanel = async () => {
  miniPanelExpanded.value = !miniPanelExpanded.value

  if (miniPanelExpanded.value) {
    await scrollToBottom()
  }
}

const ensureMiniTtsReady = () => {
  if (!isMiniMode) return

  voiceTtsRef.value?.connect()
  voiceTtsRef.value?.enable()
}

const getLatestAssistantMessage = () => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    const item = messages.value[i]
    if (item.role === 'assistant' && item.content.trim()) {
      return item.content
    }
  }

  return ''
}

const getMiniFloatingText = () => {
  if (isTyping.value) {
    return '正在回复中...'
  }

  if (miniTranscript.value.trim()) {
    return miniTranscript.value
  }

  return getLatestAssistantMessage()
}

// 涓轰簡閫愬瓧杈撳嚭
let displayQueue = ''
let isRendering = false

const sendMessage = async () => {
  const currentMessage = message.value.trim()
  const hasImportFile = !!rawJsonText.value

  if ((!currentMessage && !hasImportFile) || !props.userId) return

  if (currentMessage) {
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: currentMessage
    })

    message.value = ''
    miniTranscript.value = ''
    await scrollToBottom()
  }

  ensureMiniTtsReady()
  isTyping.value = true

  try {
    const res = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: currentMessage,
        role_name: roleName.value,
        user_id: props.userId,
        session_id: sessionId.value ?? null,
        raw_json_text: rawJsonText.value || null
      })
    })

    if (hasImportFile) {
      const data = await res.json()

      if (!res.ok || data.error) {
        console.log('chat error:', data)
        return
      }

      sessionId.value = data.session_id

      if (sessionId.value) {
        storeCurrentSessionId(sessionId.value)
        await loadMessages(sessionId.value)
      }

      clearImportedFile()
      await scrollToBottom()
      return
    }

    if (!res.ok || !res.body) {
      const errorText = await res.text()
      console.log('chat error:', errorText)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')

    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: ''
    })
    const assistantMessage = messages.value[messages.value.length - 1]
    let charsSinceLastScroll = 0

    const renderChunkByChar = async () => {
      if (isRendering) return

      isRendering = true

      while (true) {
        if (displayQueue.length === 0) {
          isRendering = false
          return
        }

        assistantMessage.content += displayQueue[0]
        displayQueue = displayQueue.slice(1)
        charsSinceLastScroll += 1

        if (charsSinceLastScroll >= 20 || displayQueue.length === 0) {
          charsSinceLastScroll = 0
          await scrollToBottom()
        }

        await new Promise((resolve) => setTimeout(resolve, 1))
      }
    }

    let receivedFirstChunk = false

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      const chunk = decoder.decode(value, { stream: true })

      if (!chunk) continue

      if (!receivedFirstChunk) {
        isTyping.value = false
        receivedFirstChunk = true
      }

      displayQueue += chunk
      void renderChunkByChar()
      voiceTtsRef.value?.appendTextChunk(chunk)
    }

    const remainingText = decoder.decode()

    if (remainingText) {
      displayQueue += remainingText
      await renderChunkByChar()
      voiceTtsRef.value?.appendTextChunk(remainingText)
    }

    voiceTtsRef.value?.flushRemainingText()
    await scrollToBottom()
  } finally {
    isTyping.value = false
  }
}

const handleVoiceText = async (text: string) => {
  message.value = text
  miniTranscript.value = text

  if (isMiniMode) return

  await nextTick()
  messageInputRef.value?.focus()
}

const handleVoiceStart = () => {
  ensureMiniTtsReady()
}

const handleVoiceSubmit = async (text: string) => {
  message.value = text
  miniTranscript.value = text
  ensureMiniTtsReady()
  await sendMessage()
}

const isTypingTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false

  const tagName = target.tagName
  return (
    tagName === 'INPUT' ||
    tagName === 'TEXTAREA' ||
    target.isContentEditable
  )
}

const handleVoiceShortcutDown = async (event: KeyboardEvent) => {
  if (event.repeat) return
  if (event.key.toLowerCase() !== 'v') return
  if (isTypingTarget(event.target)) return

  event.preventDefault()
  ensureMiniTtsReady()
  await voiceInputRef.value?.startRecording()
}

const handleVoiceShortcutUp = async (event: KeyboardEvent) => {
  if (event.key.toLowerCase() !== 'v') return
  if (isTypingTarget(event.target)) return

  event.preventDefault()
  await voiceInputRef.value?.stopRecording()
}

onMounted(() => {
  voiceTtsRef.value?.connect()
  window.addEventListener('keydown', handleVoiceShortcutDown)
  window.addEventListener('keyup', handleVoiceShortcutUp)

  if (isMiniMode) {
    nextTick(() => {
      if (!miniShellRef.value) return

      miniResizeObserver = new ResizeObserver(() => {
        queueMiniWindowResize()
      })
      miniResizeObserver.observe(miniShellRef.value)
      queueMiniWindowResize()
    })
  }

  if (props.userId) {
    changeRole()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleVoiceShortcutDown)
  window.removeEventListener('keyup', handleVoiceShortcutUp)

  if (miniResizeObserver) {
    miniResizeObserver.disconnect()
    miniResizeObserver = null
  }

  if (miniResizeTimer !== null) {
    window.clearTimeout(miniResizeTimer)
    miniResizeTimer = null
  }
})

watch(
  () => props.roleName,
  async (newRoleName) => {
    roleName.value = newRoleName
    if (props.userId) {
      await changeRole()
    }
  }
)

watch(
  () => props.userId,
  async (newUserId) => {
    if (newUserId) {
      await changeRole()
    }
  }
)

watch(miniPanelExpanded, async () => {
  await nextTick()
  queueMiniWindowResize()
})
</script>

<template>
  <section class="chat-page" :class="{ 'mini-mode': isMiniMode }">
    <template v-if="isMiniMode">
      <div ref="miniShellRef" class="mini-shell" :class="{ expanded: miniPanelExpanded }">
        <VoiceTTS
          ref="voiceTtsRef"
          :roleName="roleName"
          :autoEnable="true"
          :showButton="false"
        />

        <template v-if="miniPanelExpanded">
          <div class="mini-topbar">
            <button type="button" class="mini-top-btn" @click="toggleMiniPanel">
              收起
            </button>

            <div class="mini-role-pill">{{ roleName }}</div>

            <button type="button" class="mini-top-btn" @click="emit('go-home')">返回</button>
          </div>

          <div class="mini-panel">
            <div class="mini-control-row">
              <button type="button" class="mini-action-btn" @click="createNewSession">新会话</button>

              <select v-model="roleName" class="mini-select" @change="changeRole">
                <option value="yagami_light">yagami_light</option>
                <option value="mihaisha">mihaisha</option>
                <option value="other_role">other_role</option>
              </select>

              <select v-model="gameName" class="mini-select" @change="changeGame">
                <option value="">纯聊天</option>
                <option value="dwrg">第五人格</option>
                <option value="sister_weake">孱弱的姐妹</option>
              </select>
            </div>

            <SessionHistory
              :userId="props.userId"
              :roleName="roleName"
              :gameName="gameName"
              :currentSessionId="sessionId ?? undefined"
              :compact="true"
              @select-session="handleSelectSession"
            />

            <div ref="replyContentRef" class="reply-content mini-reply-content">
              <div v-if="messages.length === 0" class="empty-message">No messages yet</div>

              <div
                v-for="item in messages"
                :key="item.id"
                class="chat-row"
                :class="item.role"
              >
                <div class="chat-bubble">{{ item.content }}</div>
              </div>

              <div v-if="isTyping" class="chat-row assistant">
                <div class="chat-bubble typing-bubble">Typing...</div>
              </div>
            </div>

            <div class="mini-input-row">
              <input
                ref="messageInputRef"
                v-model="message"
                type="text"
                placeholder="Type your message here"
                @keyup.enter="sendMessage"
              >

              <button class="send-btn mini-send-btn" @click="sendMessage">Send</button>
            </div>
          </div>
        </template>

        <template v-else>
          <button type="button" class="mini-expand-dot" @click="toggleMiniPanel" title="展开">
            ···
          </button>

          <div v-if="getMiniFloatingText()" class="mini-floating-reply">
            {{ getMiniFloatingText() }}
          </div>

          <div class="mini-compact-bar">
            <div class="mini-voice-action">
              <VoiceInput
                ref="voiceInputRef"
                :compact="true"
                @voice-start="handleVoiceStart"
                @voice-text="handleVoiceText"
                @voice-submit="handleVoiceSubmit"
              />
            </div>
          </div>
        </template>
      </div>
    </template>

    <template v-else>
      <header class="chat-header">
        <div class="header-main">
          <button type="button" class="back-btn" @click="emit('go-home')">←</button>
          <div>
            <p class="eyebrow">Play Session</p>
            <h1>Chat Panel</h1>
            <p class="subtitle">Current role session and chat history area.</p>
          </div>
        </div>

        <div class="header-actions">
          <button type="button" class="mini-action-btn" @click="createNewSession">New</button>
          <VoiceTTS ref="voiceTtsRef" :roleName="roleName" />

          <div class="role-switcher">
            <label class="field-label" for="role-select">Role</label>
            <select id="role-select" v-model="roleName" @change="changeRole">
              <option value="yagami_light">yagami_light</option>
              <option value="mihaisha">mihaisha</option>
              <option value="other_role">other_role</option>
            </select>
          </div>

          <div class="game-switcher">
            <label class="field-label" for="game-select">Game</label>
            <select id="game-select" v-model="gameName" @change="changeGame">
              <option value="">Pure Chat</option>
              <option value="dwrg">Identity V</option>
              <option value="sister_weake">孱弱的姐妹</option>
            </select>
          </div>

          <div class="session-switcher">
            <SessionHistory
              :userId="props.userId"
              :roleName="roleName"
              :gameName="gameName"
              :currentSessionId="sessionId ?? undefined"
              :compact="true"
              @select-session="handleSelectSession"
            />
          </div>
        </div>
      </header>

      <div class="chat-layout">
        <section class="chat-card message-card">
          <div class="card-head">
            <h2>Chat Record</h2>
            <span class="status-dot"></span>
          </div>

          <div class="reply-box">
            <p class="field-label">Conversation</p>
            <div ref="replyContentRef" class="reply-content">
              <div v-if="messages.length === 0" class="empty-message">No messages yet</div>

              <div
                v-for="item in messages"
                :key="item.id"
                class="chat-row"
                :class="item.role"
              >
                <div class="chat-bubble">{{ item.content }}</div>
              </div>

              <div v-if="isTyping" class="chat-row assistant">
                <div class="chat-bubble typing-bubble">Typing...</div>
              </div>
            </div>
          </div>

          <div class="message-box">
            <label class="field-label" for="message-input">Message</label>
            <input
              ref="importFileInputRef"
              type="file"
              accept=".json,application/json"
              class="hidden-file-input"
              @change="handleImportFileChange"
            >

            <div class="file-import-row">
              <button type="button" class="file-btn" @click="openImportFilePicker">Import JSON</button>
              <span v-if="selectedFileName" class="file-name">{{ selectedFileName }}</span>
              <button
                v-if="selectedFileName"
                type="button"
                class="file-clear-btn"
                @click="clearImportedFile"
              >
                Clear
              </button>
            </div>

            <div class="input-row">
              <input
                id="message-input"
                ref="messageInputRef"
                v-model="message"
                type="text"
                placeholder="Type your message here"
                @keyup.enter="sendMessage"
              >

              <VoiceInput
                ref="voiceInputRef"
                @voice-start="handleVoiceStart"
                @voice-text="handleVoiceText"
                @voice-submit="handleVoiceSubmit"
              />

              <button class="send-btn" @click="sendMessage">Send</button>
            </div>
          </div>
        </section>

        <aside class="chat-card info-card">
          <div class="card-head">
            <h2>Session Info</h2>
            <span class="mini-badge">Live</span>
          </div>

          <div class="info-list">
            <div class="info-item">
              <span class="info-key">userId</span>
              <span class="info-value">{{ props.userId ?? 'null' }}</span>
            </div>
            <div class="info-item">
              <span class="info-key">sessionId</span>
              <span class="info-value">{{ sessionId ?? 'null' }}</span>
            </div>
            <div class="info-item">
              <span class="info-key">roleName</span>
              <span class="info-value">{{ roleName }}</span>
            </div>
            <div class="info-item">
              <span class="info-key">gameName</span>
              <span class="info-value">{{ gameName || 'pure_chat' }}</span>
            </div>
          </div>

          <SessionHistory
            :userId="props.userId"
            :roleName="roleName"
            :gameName="gameName"
            :currentSessionId="sessionId ?? undefined"
            @select-session="handleSelectSession"
          />

          <button class="new-session-btn" @click="createNewSession">New Session</button>
        </aside>
      </div>
    </template>
  </section>
</template>

<style scoped>
.chat-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top, rgba(193, 173, 255, 0.26), transparent 28%),
    linear-gradient(180deg, #faf7ff 0%, #f5f1ff 45%, #f8f6ff 100%);
}

.chat-page.mini-mode {
  height: auto;
  min-height: auto;
  overflow: hidden;
  padding: 0;
  background: transparent;
}

.mini-shell {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: fit-content;
  height: auto;
  min-height: 140px;
  position: relative;
  -webkit-app-region: drag;
  transition: width 0.2s ease, height 0.2s ease, transform 0.2s ease;
}

.mini-shell.expanded {
  min-height: max-content;
}

.mini-shell:not(.expanded) {
  width: 300px;
  min-width: 300px;
  padding-top: 10px;
  padding-bottom: 78px;
}

.mini-expand-dot {
  position: absolute;
  top: 6px;
  right: 10px;
  width: 42px;
  height: 24px;
  border: none;
  border-radius: 999px;
  font-size: 16px;
  line-height: 1;
  letter-spacing: 0.18em;
  color: #7a5ff2;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 10px 24px rgba(102, 78, 181, 0.16);
  backdrop-filter: blur(16px) saturate(135%);
  cursor: pointer;
  z-index: 10;
  pointer-events: auto;
  -webkit-app-region: no-drag;
}

.mini-floating-reply {
  position: absolute;
  left: 50%;
  bottom: 94px;
  transform: translateX(-50%);
  max-width: min(320px, 88vw);
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 13px;
  line-height: 1.55;
  color: #463971;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.34);
  box-shadow: 0 12px 28px rgba(102, 78, 181, 0.14);
  backdrop-filter: blur(20px) saturate(145%);
  white-space: pre-wrap;
  word-break: break-word;
  z-index: 3;
  pointer-events: none;
  -webkit-app-region: drag;
}

.mini-shell:not(.expanded) .mini-floating-reply {
  position: relative;
  left: auto;
  bottom: auto;
  transform: none;
  width: calc(100% - 20px);
  max-width: none;
  max-height: 180px;
  margin: 34px auto 8px;
  overflow-y: auto;
}

.mini-compact-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 14px;
  display: flex;
  justify-content: center;
  align-items: center;
  padding-bottom: 0;
  z-index: 2;
  -webkit-app-region: drag;
}

.mini-topbar {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 72px;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow: 0 12px 28px rgba(102, 78, 181, 0.14);
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-app-region: drag;
}

.mini-topbar * {
  -webkit-app-region: no-drag;
}

.mini-panel,
.mini-panel *,
.mini-action-btn,
.mini-select,
.mini-input-row input,
.mini-send-btn,
.reply-content,
.reply-content * {
  -webkit-app-region: no-drag;
}

.mini-role-pill,
.mini-label,
.mini-preview {
  -webkit-app-region: drag;
}

.mini-voice-action,
.mini-voice-action * {
  -webkit-app-region: no-drag;
}

.mini-voice-action {
  padding: 0;
}

.mini-top-btn {
  height: 38px;
  border: none;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 700;
  color: #6f52dd;
  background: rgba(255, 255, 255, 0.16);
  cursor: pointer;
}

.mini-role-pill {
  padding: 10px 14px;
  border-radius: 999px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  color: #5b42bb;
  background: rgba(255, 255, 255, 0.16);
}

.mini-voice-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 20px 16px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow: 0 16px 38px rgba(102, 78, 181, 0.16);
  backdrop-filter: blur(22px) saturate(145%);
  text-align: center;
  -webkit-app-region: drag;
}

.mini-voice-card.expanded {
  flex: 0 0 auto;
  padding: 16px 16px 20px;
}

.mini-label {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #8d6cf6;
}

.mini-preview {
  margin: 0;
  min-height: 48px;
  width: 100%;
  max-width: 100%;
  font-size: 14px;
  line-height: 1.7;
  color: #6e6586;
  white-space: pre-wrap;
  word-break: break-word;
}

.mini-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 16px 40px rgba(102, 78, 181, 0.14);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-app-region: no-drag;
}

.mini-control-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.mini-select,
.mini-input-row input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 14px;
  font-size: 14px;
  color: #2f244c;
  background: rgba(255, 255, 255, 0.22);
  outline: none;
}

.mini-reply-content {
  min-height: 140px;
  max-height: 220px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(16px) saturate(140%);
}

.mini-input-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-send-btn {
  margin-top: 0;
  align-self: stretch;
  padding: 12px 16px;
}

.mini-shell:not(.expanded) .mini-topbar,
.mini-shell:not(.expanded) .mini-panel,
.mini-shell:not(.expanded) .mini-voice-card {
  display: none;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 24px;
  padding: 28px 30px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 20px 60px rgba(170, 153, 225, 0.18);
  -webkit-app-region: drag;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 16px;
  -webkit-app-region: drag;
}

.back-btn,
.header-actions,
.header-actions *,
.chat-header select,
.chat-header button {
  -webkit-app-region: no-drag;
}

.back-btn {
  width: 46px;
  height: 46px;
  border: none;
  border-radius: 16px;
  font-size: 24px;
  line-height: 1;
  color: #6f52dd;
  background: rgba(140, 110, 248, 0.12);
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease;
}

.back-btn:hover {
  transform: translateX(-2px);
  background: rgba(140, 110, 248, 0.2);
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #8d6cf6;
}

.chat-header h1 {
  margin: 0;
  font-size: 34px;
  color: #24183d;
}

.subtitle {
  margin: 10px 0 0;
  color: #847b9b;
}

.header-actions {
  display: grid;
  grid-template-columns: 88px 88px minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  align-items: end;
  width: 100%;
}

.mini-action-btn {
  height: 46px;
  border: none;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
  color: #6f52dd;
  background: rgba(140, 110, 248, 0.12);
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.mini-action-btn:hover {
  background: rgba(140, 110, 248, 0.2);
  transform: translateY(-1px);
}

.role-switcher,
.game-switcher,
.session-switcher {
  min-width: 0;
}

.field-label {
  display: block;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #756b92;
}

.role-switcher select,
.game-switcher select,
.message-box input,
.session-select {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(142, 112, 255, 0.18);
  border-radius: 16px;
  font-size: 15px;
  color: #2f244c;
  background: rgba(255, 255, 255, 0.92);
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.role-switcher select:focus,
.game-switcher select:focus,
.message-box input:focus,
.session-select:focus,
.mini-select:focus,
.mini-input-row input:focus {
  border-color: #8c67ff;
  box-shadow: 0 0 0 4px rgba(140, 103, 255, 0.12);
}

.chat-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 24px;
  margin-top: 24px;
}

.chat-card {
  padding: 28px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 20px 60px rgba(170, 153, 225, 0.16);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.card-head h2 {
  margin: 0;
  font-size: 24px;
  color: #271b44;
}

.status-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b66ff, #b296ff);
  box-shadow: 0 0 0 8px rgba(139, 102, 255, 0.12);
}

.mini-badge {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #7c58f1;
  background: rgba(140, 110, 248, 0.12);
}

.reply-box {
  margin-bottom: 24px;
}

.reply-content {
  min-height: 360px;
  max-height: 520px;
  overflow-y: auto;
  padding: 18px;
  border: 1px solid rgba(142, 112, 255, 0.12);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(248, 245, 255, 0.92), rgba(255, 255, 255, 0.78));
}

.chat-row {
  display: flex;
  margin-bottom: 14px;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-row.user .chat-bubble {
  color: #ffffff;
  background: linear-gradient(90deg, #7f5bff, #a586ff);
}

.chat-row.assistant .chat-bubble {
  color: #3e335b;
  background: rgba(140, 110, 248, 0.12);
}

.typing-bubble {
  opacity: 0.75;
  font-style: italic;
}

.empty-message {
  color: #8b7fa8;
  text-align: center;
  padding: 40px 0;
}

.message-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hidden-file-input {
  display: none;
}

.file-import-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.file-btn,
.file-clear-btn {
  border: none;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.file-btn {
  padding: 10px 14px;
  color: #6f52dd;
  background: rgba(140, 110, 248, 0.12);
}

.file-clear-btn {
  padding: 8px 12px;
  color: #8a5873;
  background: rgba(255, 160, 190, 0.18);
}

.file-name {
  max-width: 260px;
  font-size: 13px;
  color: #6d6289;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-row input {
  flex: 1;
  min-width: 0;
}

.send-btn {
  margin-top: 3px;
  flex-shrink: 0;
  align-self: flex-start;
  padding: 12px 20px;
  border: none;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(90deg, #7f5bff, #a586ff);
  box-shadow: 0 14px 30px rgba(132, 96, 255, 0.24);
  cursor: pointer;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(140, 110, 248, 0.08);
}

.info-key {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8b7fa8;
}

.info-value {
  font-size: 16px;
  font-weight: 600;
  color: #2e234b;
  word-break: break-word;
}

.new-session-btn {
  width: 100%;
  margin-top: 18px;
  padding: 14px 16px;
  border: none;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(90deg, #8b66ff, #b296ff);
  box-shadow: 0 14px 30px rgba(132, 96, 255, 0.2);
  cursor: pointer;
}

@media (max-width: 820px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .chat-header {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 760px) {
  .chat-page:not(.mini-mode) {
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 12px;
  }

  .chat-header {
    padding: 14px 16px;
    border-radius: 20px;
    gap: 14px;
  }

  .header-main {
    gap: 12px;
  }

  .chat-header h1 {
    font-size: 22px;
  }

  .subtitle,
  .eyebrow {
    display: none;
  }

  .header-actions {
    grid-template-columns: 88px 88px minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
    align-items: end;
    width: 100%;
  }

  .chat-layout {
    flex: 1;
    min-height: 0;
    display: block;
    margin-top: 12px;
  }

  .message-card {
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 16px;
    border-radius: 22px;
  }

  .info-card {
    display: none;
  }

  .card-head {
    margin-bottom: 14px;
  }

  .card-head h2 {
    font-size: 20px;
  }

  .reply-box {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }

  .reply-content {
    flex: 1;
    min-height: 0;
    max-height: none;
    padding: 14px;
    border-radius: 18px;
  }

  .chat-bubble {
    max-width: 88%;
    padding: 10px 14px;
    line-height: 1.6;
  }

  .message-box {
    gap: 8px;
  }

  .message-box .field-label {
    display: block;
    margin-bottom: 4px;
  }

  .input-row {
    gap: 8px;
  }

  .send-btn {
    padding: 12px 16px;
  }
}

@media (max-width: 720px) {
  .chat-page:not(.mini-mode) {
    padding: 18px;
  }

  .chat-header,
  .chat-card {
    padding: 22px;
  }
}
</style>
