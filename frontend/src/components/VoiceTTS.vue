<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  roleName: {
    type: String,
    default: 'other_role'
  },
  autoEnable: {
    type: Boolean,
    default: false
  },
  showButton: {
    type: Boolean,
    default: true
  }
})

const FLUSH_CHAR_THRESHOLD = 12
const FLUSH_DELAY_MS = 320
const wordSegmenter = new Intl.Segmenter('zh-CN', {
  granularity: 'word'
})

const ttsEnabled = ref(false)
const audioContext = ref<AudioContext | null>(null)
const audioQueue = ref<ArrayBuffer[]>([])
const isAudioPlaying = ref(false)
const nextPlayTime = ref(0)
const ttsSocket = ref<WebSocket | null>(null)
const sentenceBuffer = ref('')

let flushTimer: ReturnType<typeof setTimeout> | null = null

const clearFlushTimer = () => {
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
}

const sendTtsMessage = (payload: Record<string, unknown>) => {
  if (!ttsSocket.value) return
  if (ttsSocket.value.readyState !== WebSocket.OPEN) return

  ttsSocket.value.send(JSON.stringify(payload))
}

const syncRole = () => {
  sendTtsMessage({
    type: 'set_role',
    role_name: props.roleName
  })
}

const sendTextToTts = (text: string) => {
  if (!text) return

  sendTtsMessage({
    type: 'append_text',
    text
  })

  sendTtsMessage({
    type: 'commit'
  })
}

const flushSentence = () => {
  if (!ttsEnabled.value) return

  const match = sentenceBuffer.value.match(/^(.*?[。！？!?])/)

  if (!match) return

  const sentence = match[1].trim()
  sentenceBuffer.value = sentenceBuffer.value.slice(match[1].length)

  if (!sentence) return

  sendTextToTts(sentence)
}

const flushSentenceSafe = () => {
  flushSentence()
}

const flushSentenceRealtime = () => {
  flushSentence()
}

const getWordChunk = (text: string, minLength = FLUSH_CHAR_THRESHOLD) => {
  let end = 0

  for (const item of wordSegmenter.segment(text)) {
    end += item.segment.length

    if (end >= minLength) {
      return {
        chunk: text.slice(0, end),
        rest: text.slice(end)
      }
    }
  }

  return null
}

const flushByThreshold = () => {
  if (!ttsEnabled.value) return false

  const wordChunk = getWordChunk(sentenceBuffer.value)
  if (!wordChunk) return false

  const chunk = wordChunk.chunk.trim()
  sentenceBuffer.value = wordChunk.rest

  if (!chunk) return false

  sendTextToTts(chunk)
  return true
}

const scheduleFlush = () => {
  if (!ttsEnabled.value) return

  clearFlushTimer()
  flushTimer = setTimeout(() => {
    flushTimer = null

    flushByThreshold()
  }, FLUSH_DELAY_MS)
}

const createAudioContext = () => {
  if (!audioContext.value) {
    audioContext.value = new AudioContext({ sampleRate: 24000 })
  }

  return audioContext.value
}

const pcmArrayBufferToAudioBuffer = (arrayBuffer: ArrayBuffer) => {
  const context = createAudioContext()
  const int16Array = new Int16Array(arrayBuffer)
  const audioBuffer = context.createBuffer(1, int16Array.length, 24000)
  const channelData = audioBuffer.getChannelData(0)

  for (let i = 0; i < int16Array.length; i += 1) {
    channelData[i] = int16Array[i] / 32768
  }

  return audioBuffer
}

const playAudioQueue = async () => {
  if (isAudioPlaying.value) return
  if (audioQueue.value.length === 0) return

  isAudioPlaying.value = true

  try {
    const context = createAudioContext()

    if (context.state === 'suspended') {
      await context.resume()
    }

    while (audioQueue.value.length > 0) {
      const chunk = audioQueue.value.shift()
      if (!chunk) continue

      const audioBuffer = pcmArrayBufferToAudioBuffer(chunk)
      const source = context.createBufferSource()
      source.buffer = audioBuffer
      source.connect(context.destination)

      const now = context.currentTime
      const startTime = Math.max(now, nextPlayTime.value)
      source.start(startTime)
      nextPlayTime.value = startTime + audioBuffer.duration
    }
  } finally {
    isAudioPlaying.value = false
  }
}

const connect = () => {
  if (
    ttsSocket.value &&
    (
      ttsSocket.value.readyState === WebSocket.OPEN ||
      ttsSocket.value.readyState === WebSocket.CONNECTING
    )
  ) {
    return
  }

  ttsSocket.value = new WebSocket('ws://127.0.0.1:8000/voice/tts/ws')
  ttsSocket.value.binaryType = 'arraybuffer'

  ttsSocket.value.onopen = () => {
    console.log('VoiceTTS websocket connected')
    syncRole()
  }

  ttsSocket.value.onmessage = async (event) => {
    if (event.data instanceof ArrayBuffer) {
      audioQueue.value.push(event.data)
      void playAudioQueue()
      return
    }

    if (event.data instanceof Blob) {
      const arrayBuffer = await event.data.arrayBuffer()
      audioQueue.value.push(arrayBuffer)
      void playAudioQueue()
      return
    }

    console.log('VoiceTTS receive message:', event.data)
  }

  ttsSocket.value.onclose = () => {
    console.log('VoiceTTS websocket closed')
  }

  ttsSocket.value.onerror = (error) => {
    console.log('VoiceTTS websocket error:', error)
  }
}

const appendTextChunk = (chunk: string) => {
  if (!ttsEnabled.value) return
  if (!chunk) return

  sentenceBuffer.value += chunk

  while (true) {
    const before = sentenceBuffer.value
    flushSentenceRealtime()

    if (sentenceBuffer.value === before) {
      break
    }
  }

  while (flushByThreshold()) {
    clearFlushTimer()
  }

  if (sentenceBuffer.value.trim()) {
    scheduleFlush()
  }
}

const flushRemainingText = () => {
  if (!ttsEnabled.value) return

  clearFlushTimer()
  const text = sentenceBuffer.value.trim()
  if (!text) return

  sendTextToTts(text)
  sentenceBuffer.value = ''
}

const close = () => {
  if (ttsSocket.value) {
    ttsSocket.value.close()
    ttsSocket.value = null
  }

  if (audioContext.value) {
    void audioContext.value.close()
    audioContext.value = null
  }

  audioQueue.value = []
  nextPlayTime.value = 0
  clearFlushTimer()
}

const enable = () => {
  if (ttsEnabled.value) {
    connect()
    if (audioContext.value) {
      void audioContext.value.resume()
    }
    return
  }

  ttsEnabled.value = true
  void createAudioContext().resume()
  connect()
}

const disable = () => {
  if (!ttsEnabled.value) return

  ttsEnabled.value = false
  sentenceBuffer.value = ''
  audioQueue.value = []
  clearFlushTimer()
}

const toggleTts = () => {
  if (ttsEnabled.value) {
    disable()
    return
  }

  enable()
}

defineExpose({
  connect,
  enable,
  disable,
  appendTextChunk,
  flushSentence,
  flushRemainingText,
  flushSentenceSafe,
  close,
})

onBeforeUnmount(() => {
  close()
})

watch(
  () => props.roleName,
  () => {
    syncRole()
  }
)

watch(
  () => props.autoEnable,
  (newValue) => {
    if (newValue) {
      connect()
    }
  },
  { immediate: true }
)
</script>

<template>
  <button
    v-if="props.showButton"
    type="button"
    class="tts-toggle-btn"
    :class="{ active: ttsEnabled }"
    @click="toggleTts"
  >
    {{ ttsEnabled ? '语音开' : '语音关' }}
  </button>
</template>

<style scoped>
.tts-toggle-btn {
  padding: 10px 14px;
  border: none;
  border-radius: 12px;
  background: rgba(140, 110, 248, 0.12);
  color: #6f52dd;
  cursor: pointer;
  transition: 0.2s ease;
}

.tts-toggle-btn.active {
  background: linear-gradient(90deg, #7f5bff, #a586ff);
  color: white;
}
</style>
