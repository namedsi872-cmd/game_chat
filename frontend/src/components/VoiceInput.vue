<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  large: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits<{
  (e: 'voice-text', text: string): void
  (e: 'voice-submit', text: string): void
  (e: 'voice-start'): void
  (e: 'voice-stop'): void
}>()

const isRecording = ref(false)
const latestText = ref('')
const lastSubmittedText = ref('')

let audioContext: AudioContext | null = null
let mediaStream: MediaStream | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let processorNode: ScriptProcessorNode | null = null
let ws: WebSocket | null = null

const WS_URL = 'ws://127.0.0.1:8000/voice/asr/ws'
const TARGET_SAMPLE_RATE = 16000

const downsampleBuffer = (
  buffer: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
) => {
  if (outputSampleRate === inputSampleRate) {
    return buffer
  }

  if (outputSampleRate > inputSampleRate) {
    throw new Error('outputSampleRate should be lower than inputSampleRate')
  }

  const sampleRateRatio = inputSampleRate / outputSampleRate
  const newLength = Math.round(buffer.length / sampleRateRatio)
  const result = new Float32Array(newLength)
  let offsetResult = 0
  let offsetBuffer = 0

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio)
    let accum = 0
    let count = 0

    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i]
      count += 1
    }

    result[offsetResult] = count > 0 ? accum / count : 0
    offsetResult += 1
    offsetBuffer = nextOffsetBuffer
  }

  return result
}

const floatTo16BitPCM = (input: Float32Array) => {
  const output = new Int16Array(input.length)

  for (let i = 0; i < input.length; i += 1) {
    const s = Math.max(-1, Math.min(1, input[i]))
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }

  return output
}

const stopStream = async () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'stop' }))
  }

  if (processorNode) {
    processorNode.disconnect()
    processorNode = null
  }

  if (sourceNode) {
    sourceNode.disconnect()
    sourceNode = null
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }

  if (audioContext) {
    await audioContext.close()
    audioContext = null
  }

  if (ws) {
    ws.close()
    ws = null
  }
}

const startRecording = async () => {
  if (isRecording.value) return

  latestText.value = ''
  lastSubmittedText.value = ''
  emit('voice-start')

  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  audioContext = new AudioContext()

  sourceNode = audioContext.createMediaStreamSource(mediaStream)
  processorNode = audioContext.createScriptProcessor(4096, 1, 1)

  ws = new WebSocket(WS_URL)
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    ws?.send(JSON.stringify({ type: 'start' }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'result' && data.text) {
        latestText.value = data.text
        emit('voice-text', data.text)

        if (data.sentence_end && data.text !== lastSubmittedText.value) {
          lastSubmittedText.value = data.text
          emit('voice-submit', data.text)
        }
      }
    } catch (error) {
      console.log('voice asr ws parse error:', error)
    }
  }

  ws.onerror = (error) => {
    console.log('voice asr ws error:', error)
  }

  processorNode.onaudioprocess = (event) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const input = event.inputBuffer.getChannelData(0)
    const downsampled = downsampleBuffer(
      input,
      audioContext?.sampleRate ?? 48000,
      TARGET_SAMPLE_RATE
    )
    const pcm16 = floatTo16BitPCM(downsampled)
    ws.send(pcm16.buffer)
  }

  sourceNode.connect(processorNode)
  processorNode.connect(audioContext.destination)

  isRecording.value = true
}

const stopRecording = async () => {
  if (!isRecording.value) return

  const pendingText = latestText.value.trim()

  if (pendingText && pendingText !== lastSubmittedText.value) {
    lastSubmittedText.value = pendingText
    emit('voice-submit', pendingText)
  }

  isRecording.value = false
  emit('voice-stop')
  await stopStream()
}

defineExpose({
  startRecording,
  stopRecording
})
</script>

<template>
  <div class="voice-input" :class="{ large: props.large, compact: props.compact }">
    <button
      class="voice-btn"
      :class="{ recording: isRecording, large: props.large, compact: props.compact }"
      @pointerdown="startRecording"
      @pointerup="stopRecording"
      @pointerleave="stopRecording"
      @pointercancel="stopRecording"
      type="button"
      title="按住说话"
    >
      {{ props.large ? '按住说话' : '语' }}
    </button>
  </div>
</template>

<style scoped>
.voice-input {
  flex-shrink: 0;
}

.voice-input.large {
  width: 100%;
  display: flex;
  justify-content: center;
}

.voice-input.compact {
  width: auto;
  display: inline-flex;
  justify-content: center;
}

.voice-btn {
  width: 46px;
  height: 46px;
  border: none;
  border-radius: 50%;
  background: rgba(140, 110, 248, 0.12);
  color: #6f52dd;
  font-size: 20px;
  cursor: pointer;
  transition: 0.2s ease;
}

.voice-btn.large {
  width: min(220px, 70vw);
  height: 72px;
  border-radius: 999px;
  font-size: 20px;
  font-weight: 700;
}

.voice-btn.compact {
  width: min(170px, 58vw);
  height: 44px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 700;
}

.voice-btn:hover {
  background: rgba(140, 110, 248, 0.2);
}

.voice-btn.recording {
  background: linear-gradient(90deg, #7f5bff, #a586ff);
  color: white;
}
</style>
