<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppSidebar from '../components/AppSidebar.vue'

type PlayRecord = {
  session_id: number
  title: string
  role_name: string
  updated_at: string
  last_message: string
}

const props = defineProps<{
  userId: number | undefined
  username: string | undefined
}>()

const emit = defineEmits<{
  (e: 'login'): void
  (e: 'go-home'): void
  (e: 'start-play'): void
}>()

const records = ref<PlayRecord[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 5
const total = ref(0)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const canPrev = computed(() => page.value > 1)
const canNext = computed(() => page.value < totalPages.value)

const formatTime = (value: string) => {
  if (!value) return '暂无时间'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadRecords = async () => {
  if (!props.userId) {
    records.value = []
    total.value = 0
    return
  }

  loading.value = true
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/records/${props.userId}?page=${page.value}&page_size=${pageSize}`
    )
    const data = await res.json()
    records.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

const prevPage = async () => {
  if (!canPrev.value) return
  page.value -= 1
  await loadRecords()
}

const nextPage = async () => {
  if (!canNext.value) return
  page.value += 1
  await loadRecords()
}

watch(
  () => props.userId,
  async () => {
    page.value = 1
    await loadRecords()
  }
)

onMounted(async () => {
  await loadRecords()
})
</script>

<template>
  <div class="records-page">
    <AppSidebar
      class="records-sidebar"
      activePage="records"
      @login="emit('login')"
      @go-home="emit('go-home')"
      @go-records="loadRecords"
    />

    <main class="records-main">
      <div class="topbar">
        <div class="title-block">
          <p class="eyebrow">Play Records</p>
          <h1>陪玩记录</h1>
          <p class="subtitle">这里专门承接历史陪玩会话，后面你还可以继续往这里加筛选、搜索和跳转聊天。</p>
        </div>

        <div class="user-box">
          <div class="user-avatar">{{ props.username || '未' }}</div>
          <div>
            <p class="user-name">{{ props.username || '未登录' }}</p>
            <span class="user-level">
              {{ props.userId ? `用户ID ${props.userId}` : '点击左下角登录' }}
            </span>
          </div>
        </div>
      </div>

      <section v-if="!props.userId" class="empty-shell">
        <div class="empty-mark">☁</div>
        <h2>还没有登录</h2>
        <p>陪玩记录按用户维度查看，所以这里需要先拿到你的用户编号。</p>
        <div class="empty-actions">
          <button type="button" class="primary-btn" @click="emit('login')">去登录</button>
          <button type="button" class="ghost-btn" @click="emit('go-home')">返回首页</button>
        </div>
      </section>

      <section v-else class="records-card">
        <div class="records-head">
          <div>
            <h2>历史会话</h2>
            <p>每条记录都显示会话标题、所属角色、最后一条消息和最近更新时间。</p>
          </div>
          <button type="button" class="primary-btn" @click="emit('start-play')">开始新的陪玩</button>
        </div>

        <div v-if="loading" class="state-box">记录加载中...</div>

        <div v-else-if="records.length === 0" class="state-box">
          还没有陪玩记录，先去首页开启第一场对话吧。
        </div>

        <div v-else class="record-list">
          <article v-for="item in records" :key="item.session_id" class="record-item">
            <div class="record-top">
              <div>
                <h3>{{ item.title }}</h3>
                <p class="role-chip">{{ item.role_name }}</p>
              </div>
              <time class="record-time">{{ formatTime(item.updated_at) }}</time>
            </div>

            <p class="record-preview">
              {{ item.last_message || '这个会话还没有消息内容。' }}
            </p>

            <div class="record-foot">
              <span>Session ID: {{ item.session_id }}</span>
            </div>
          </article>
        </div>

        <div class="pager">
          <button type="button" class="ghost-btn" :disabled="!canPrev" @click="prevPage">
            上一页
          </button>
          <span class="pager-text">第 {{ page }} / {{ totalPages }} 页</span>
          <button type="button" class="ghost-btn" :disabled="!canNext" @click="nextPage">
            下一页
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
:global(body) {
  margin: 0;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background:
    radial-gradient(circle at top, rgba(197, 182, 255, 0.42), transparent 35%),
    linear-gradient(180deg, #faf7ff 0%, #f5f1ff 45%, #f8f6ff 100%);
  color: #261c40;
}

:global(*) {
  box-sizing: border-box;
}

.records-page {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  min-height: 100vh;
}

.records-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
}

.records-main {
  padding: 24px 28px 28px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #8f74ff;
}

.title-block h1 {
  margin: 0;
  font-size: 42px;
  color: #291d48;
}

.subtitle {
  max-width: 720px;
  margin: 12px 0 0;
  line-height: 1.7;
  color: #817798;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 10px 26px rgba(181, 169, 228, 0.16);
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #af9dff, #815fff);
}

.user-name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #2b1f47;
}

.user-level {
  display: inline-flex;
  margin-top: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: #ffffff;
  background: linear-gradient(135deg, #a579ff, #8458ff);
  border-radius: 999px;
}

.records-card,
.empty-shell {
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 22px 60px rgba(181, 169, 228, 0.16);
}

.records-card {
  padding: 28px;
}

.records-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  margin-bottom: 24px;
}

.records-head h2 {
  margin: 0;
  font-size: 28px;
  color: #281d45;
}

.records-head p {
  margin: 8px 0 0;
  color: #8c84a4;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.record-item {
  padding: 22px;
  border: 1px solid rgba(145, 120, 255, 0.12);
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(253, 251, 255, 0.98), rgba(246, 240, 255, 0.96));
}

.record-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.record-top h3 {
  margin: 0 0 10px;
  font-size: 22px;
  color: #2c2148;
}

.role-chip {
  display: inline-flex;
  margin: 0;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #7b59f4;
  background: rgba(140, 117, 255, 0.12);
}

.record-time {
  white-space: nowrap;
  font-size: 13px;
  color: #9187ab;
}

.record-preview {
  margin: 16px 0 0;
  line-height: 1.75;
  color: #5f5677;
}

.record-foot {
  margin-top: 14px;
  font-size: 13px;
  color: #9a93b0;
}

.pager {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.pager-text {
  font-size: 14px;
  color: #7f7698;
}

.primary-btn,
.ghost-btn {
  border: none;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn {
  padding: 14px 20px;
  color: #ffffff;
  background: linear-gradient(90deg, #7f5bff, #a586ff);
  box-shadow: 0 14px 30px rgba(132, 96, 255, 0.24);
}

.ghost-btn {
  padding: 12px 18px;
  color: #6c58b5;
  background: rgba(140, 117, 255, 0.12);
}

.ghost-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.state-box,
.empty-shell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.state-box {
  min-height: 240px;
  border-radius: 24px;
  color: #7a7192;
  background: rgba(247, 243, 255, 0.9);
}

.empty-shell {
  min-height: 520px;
  padding: 32px;
}

.empty-mark {
  font-size: 72px;
  color: rgba(142, 112, 255, 0.28);
}

.empty-shell h2 {
  margin: 16px 0 8px;
  font-size: 30px;
  color: #2b2047;
}

.empty-shell p {
  max-width: 420px;
  margin: 0;
  line-height: 1.8;
  color: #887f9f;
}

.empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

@media (max-width: 1100px) {
  .records-page {
    grid-template-columns: 1fr;
  }

  .records-sidebar {
    position: relative;
    height: auto;
  }

  .topbar,
  .records-head,
  .pager {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .records-main {
    padding: 18px;
  }

  .records-card,
  .empty-shell {
    padding: 20px;
  }

  .title-block h1 {
    font-size: 34px;
  }

  .empty-actions {
    flex-direction: column;
    width: 100%;
  }
}
</style>
