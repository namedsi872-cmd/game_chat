<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

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
  },
  currentSessionId: {
    type: Number,
    default: null
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits<{
  (e: 'select-session', sessionId: number): void
}>()

const sessions = ref<any[]>([])
const selectedSessionId = ref('')

const getGameLabel = (gameName: string | null) => {
  if (gameName === 'dwrg') return '第五人格'
  return '纯聊天'
}

const labelText = computed(() =>
  props.compact ? 'Session' : '历史会话'
)

const loadSessions = async () => {
  if (!props.userId) return

  const res = await fetch(
    `http://127.0.0.1:8000/sessions/list/${props.userId}/${props.roleName}?game_name=${encodeURIComponent(props.gameName || '')}`
  )
  const data = await res.json()
  sessions.value = data.sessions || []
  selectedSessionId.value = props.currentSessionId ? String(props.currentSessionId) : ''
}

const handleSelectChange = () => {
  const sessionId = Number(selectedSessionId.value)
  if (!sessionId) return
  emit('select-session', sessionId)
}

onMounted(loadSessions)

watch(() => props.roleName, loadSessions)
watch(() => props.gameName, loadSessions)
watch(() => props.userId, loadSessions)
watch(
  () => props.currentSessionId,
  async (newSessionId) => {
    selectedSessionId.value = newSessionId ? String(newSessionId) : ''
    await loadSessions()
  }
)
</script>

<template>
  <div class="session-history" :class="{ compact: props.compact }">
    <template v-if="props.compact">
      <label class="history-title" for="session-select">{{ labelText }}</label>
      <select
        id="session-select"
        v-model="selectedSessionId"
        class="session-select"
        @change="handleSelectChange"
      >
        <option value="">最新会话</option>
        <option
          v-for="item in sessions"
          :key="item.id"
          :value="String(item.id)"
        >
          {{ item.title || `会话 ${item.id}` }} · {{ getGameLabel(item.game_name) }}
        </option>
      </select>
    </template>

    <template v-else>
      <div class="history-title">{{ labelText }}</div>

      <div class="history-list">
        <div
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ active: item.id === currentSessionId }"
          @click="emit('select-session', item.id)"
        >
          <div class="session-name">
            {{ item.title || `会话 ${item.id}` }}
          </div>
          <div class="session-meta">
            {{ getGameLabel(item.game_name) }} · session_id: {{ item.id }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.session-history {
  margin-top: 20px;
}

.session-history.compact {
  margin-top: 0;
}

.history-title {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #6f5b96;
}

.session-select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(142, 112, 255, 0.18);
  border-radius: 16px;
  font-size: 14px;
  color: #2f244c;
  background: rgba(255, 255, 255, 0.92);
  outline: none;
}

.session-item {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(140, 110, 248, 0.08);
  cursor: pointer;
  transition: 0.2s ease;
}

.session-item + .session-item {
  margin-top: 10px;
}

.session-item:hover {
  background: rgba(140, 110, 248, 0.15);
}

.session-item.active {
  border: 1px solid rgba(127, 91, 255, 0.5);
  background: rgba(140, 110, 248, 0.18);
}

.session-name {
  font-size: 15px;
  font-weight: 600;
  color: #2e234b;
}

.session-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #8b7fa8;
}

.history-list {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 6px;
}
</style>
