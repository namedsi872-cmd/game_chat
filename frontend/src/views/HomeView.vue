<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import AppSidebar from '../components/AppSidebar.vue'
import CharacterCard from '../components/CharacterCard.vue'

type RecordPreview = {
  session_id: number
  title: string
  role_name: string
  updated_at: string
  last_message: string
}

const characters = [
  {
    roleName: 'yagami_light',
    name: '夜神月',
    summary: '偏策略、偏分析、偏压迫感的高冷型陪玩，适合训练思路和复盘表达。',
    tags: ['技术流', '高冷', '可靠'],
    theme: 'light' as const,
  },
  {
    roleName: 'mihaisha',
    name: '弥海砂',
    summary: '更轻松、更活泼的陪玩风格，适合日常陪聊和低压力互动。',
    tags: ['可爱', '温柔', '活泼'],
    theme: 'dark' as const,
  },
]

const emit = defineEmits<{
  (e: 'login'): void
  (e: 'start_Play'): void
  (e: 'change_role', roleName: string): void
  (e: 'change_game', gameName: string): void
  (e: 'go-records'): void
}>()

const props = defineProps<{
  userId: number | undefined
  username: string | undefined
  roleName: string | undefined
  gameName: string | undefined
}>()

const recentRecords = ref<RecordPreview[]>([])
const recordsLoading = ref(false)

const formatTime = (value: string) => {
  if (!value) return '暂无时间'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadRecentRecords = async () => {
  if (!props.userId) {
    recentRecords.value = []
    return
  }

  recordsLoading.value = true
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/records/${props.userId}?page=1&page_size=3`
    )
    const data = await res.json()
    recentRecords.value = data.records || []
  } finally {
    recordsLoading.value = false
  }
}

const handleGameChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('change_game', target.value)
}

watch(
  () => props.userId,
  async () => {
    await loadRecentRecords()
  }
)

onMounted(async () => {
  await loadRecentRecords()
})
</script>

<template>
  <div class="home-page">
    <AppSidebar
      class="home-sidebar"
      activePage="home"
      @login="emit('login')"
      @go-records="emit('go-records')"
    />

    <main class="home-main">
      <div class="topbar">
        <button type="button" class="notify-btn">●</button>
        <div class="user-box">
          <div class="user-avatar">{{ props.username || '未' }}</div>
          <div>
            <p class="user-name">
              {{ props.username || '未登录' }}
            </p>
            <span class="user-level">
              {{ props.userId ? '已登录' : '点击左下角登录' }}
            </span>
          </div>
        </div>
      </div>

      <div class="content-grid">
        <section class="center-column">
          <section class="hero-card">
            <div class="hero-copy">
              <h1>你的专属<span>游戏陪玩</span></h1>
              <p>24 小时在线陪伴，懂游戏，也更懂你。</p>
              <button type="button" class="start-btn" @click="emit('start_Play')">开始陪玩</button>
              <div class="game-mode-picker">
                <label for="home-game-mode">游戏模式</label>
                <select
                  id="home-game-mode"
                  :value="props.gameName || ''"
                  @change="handleGameChange"
                >
                  <option value="">纯聊天</option>
                  <option value="dwrg">第五人格</option>
                </select>
              </div>
            </div>

            <div class="hero-visual">
              <div class="hero-orb"></div>
              <div class="hero-figure">AI</div>
            </div>
          </section>

          <section class="character-section">
            <div class="section-head">
              <div>
                <h2>选择你的陪玩角色</h2>
                <p>和 TA 一起开启今天的对话吧</p>
              </div>
              <button type="button" class="text-link">角色介绍</button>
            </div>

            <div class="character-grid">
              <CharacterCard
                v-for="item in characters"
                :key="item.name"
                :name="item.name"
                :summary="item.summary"
                :tags="item.tags"
                :theme="item.theme"
                :selected="props.roleName === item.roleName"
                @select="emit('change_role', item.roleName)"
              />
            </div>
          </section>
        </section>

        <aside class="right-column">
          <section class="side-card">
            <h3>快速开始</h3>
            <button type="button" class="quick-item">
              <span class="quick-icon">●</span>
              <span>
                <strong>语音陪玩</strong>
                <small>实时语音互动</small>
              </span>
              <em>→</em>
            </button>
            <button type="button" class="quick-item">
              <span class="quick-icon">■</span>
              <span>
                <strong>文字聊天</strong>
                <small>随时畅聊陪伴</small>
              </span>
              <em>→</em>
            </button>
          </section>

          <section class="side-card stats-card">
            <h3>我的陪玩时长</h3>
            <div class="hours">2.5 <span>小时</span></div>
            <p>本周累计陪伴</p>
            <div class="clock-mark">●</div>
          </section>

          <section class="side-card records-card">
            <div class="record-head">
              <h3>最近陪玩记录</h3>
              <button type="button" class="more-link" @click="emit('go-records')">更多</button>
            </div>

            <div v-if="!props.userId" class="record-empty">
              <div class="empty-icon">☽</div>
              <p class="empty-title">登录后可查看</p>
              <p class="empty-copy">你的最近陪玩记录会显示在这里</p>
            </div>

            <div v-else-if="recordsLoading" class="record-empty">
              <div class="empty-icon">◌</div>
              <p class="empty-title">记录加载中</p>
              <p class="empty-copy">正在读取你最近的会话</p>
            </div>

            <div v-else-if="recentRecords.length === 0" class="record-empty">
              <div class="empty-icon">☽</div>
              <p class="empty-title">暂无记录</p>
              <p class="empty-copy">开始一次陪玩后，这里就会出现最新记录</p>
            </div>

            <div v-else class="record-preview-list">
              <article
                v-for="item in recentRecords"
                :key="item.session_id"
                class="record-preview-item"
              >
                <div class="record-preview-top">
                  <strong>{{ item.title }}</strong>
                  <span>{{ formatTime(item.updated_at) }}</span>
                </div>

                <p class="record-role">{{ item.role_name }}</p>
                <p class="record-message">
                  {{ item.last_message || '这个会话还没有消息内容。' }}
                </p>
              </article>
            </div>
          </section>
        </aside>
      </div>

      <footer class="page-footer">陪玩智能体 · 24 小时在你身边</footer>
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

.home-page {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  min-height: 100vh;
}

.home-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
}

.home-main {
  padding: 24px 28px 18px;
}

.topbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 18px;
  margin-bottom: 18px;
}

.notify-btn {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 50%;
  font-size: 18px;
  color: #6c5fb0;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 10px 26px rgba(181, 169, 228, 0.16);
  cursor: pointer;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
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

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
}

.center-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: center;
  overflow: hidden;
  min-height: 360px;
  padding: 40px 44px;
  border-radius: 34px;
  background:
    radial-gradient(circle at 78% 18%, rgba(166, 140, 255, 0.26), transparent 18%),
    radial-gradient(circle at 10% 82%, rgba(197, 185, 255, 0.34), transparent 22%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(245, 239, 255, 0.96));
  box-shadow: 0 26px 70px rgba(179, 164, 228, 0.2);
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.16;
  color: #251a40;
}

.hero-copy span {
  color: #7e5dff;
}

.hero-copy p {
  margin: 18px 0 0;
  font-size: 20px;
  color: #7f7699;
}

.start-btn {
  margin-top: 34px;
  padding: 16px 26px;
  border: none;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(90deg, #7f5bff, #a586ff);
  box-shadow: 0 14px 30px rgba(132, 96, 255, 0.28);
  cursor: pointer;
}

.game-mode-picker {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.game-mode-picker label {
  font-size: 14px;
  font-weight: 700;
  color: #655a82;
}

.game-mode-picker select {
  min-width: 150px;
  padding: 11px 14px;
  border: 1px solid rgba(126, 93, 255, 0.2);
  border-radius: 14px;
  color: #342750;
  background: rgba(255, 255, 255, 0.88);
  outline: none;
  cursor: pointer;
}

.game-mode-picker select:focus {
  border-color: #8c67ff;
  box-shadow: 0 0 0 4px rgba(140, 103, 255, 0.12);
}

.hero-visual {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 320px;
}

.hero-orb {
  position: absolute;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(146, 114, 255, 0.32), rgba(255, 255, 255, 0.02) 68%);
}

.hero-figure {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 220px;
  height: 280px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 120px 120px 28px 28px;
  font-size: 58px;
  font-weight: 700;
  color: #7654f3;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(233, 223, 255, 0.76));
  box-shadow: 0 24px 60px rgba(170, 148, 240, 0.24);
}

.character-section {
  padding: 30px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 22px 60px rgba(181, 169, 228, 0.16);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 22px;
}

.section-head h2 {
  margin: 0 0 8px;
  font-size: 26px;
  color: #281d45;
}

.section-head p {
  margin: 0;
  color: #8c84a4;
}

.text-link,
.more-link {
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 600;
  color: #8b68ff;
  cursor: pointer;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.right-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.side-card {
  padding: 26px 24px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 22px 60px rgba(181, 169, 228, 0.16);
}

.side-card h3 {
  margin: 0 0 18px;
  font-size: 24px;
  color: #281d45;
}

.quick-item {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 16px 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.quick-item + .quick-item {
  border-top: 1px solid rgba(140, 117, 255, 0.08);
}

.quick-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  color: #7a58f1;
  background: rgba(142, 112, 255, 0.12);
}

.quick-item strong {
  display: block;
  margin-bottom: 4px;
  font-size: 17px;
  color: #32264e;
}

.quick-item small {
  font-size: 13px;
  color: #8f86a8;
}

.quick-item em {
  font-style: normal;
  font-size: 22px;
  color: #9b87d6;
}

.stats-card {
  position: relative;
  overflow: hidden;
}

.hours {
  font-size: 56px;
  font-weight: 700;
  color: #2c2046;
}

.hours span {
  font-size: 20px;
  font-weight: 500;
  color: #7a7395;
}

.stats-card p {
  margin: 10px 0 0;
  color: #8f86a8;
}

.clock-mark {
  position: absolute;
  right: 24px;
  bottom: 24px;
  font-size: 64px;
  color: rgba(155, 133, 224, 0.16);
}

.record-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.records-card {
  min-height: 320px;
}

.record-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  text-align: center;
}

.empty-icon {
  font-size: 56px;
  color: rgba(155, 133, 224, 0.28);
}

.empty-title {
  margin: 14px 0 8px;
  font-size: 20px;
  font-weight: 700;
  color: #6d6387;
}

.empty-copy {
  margin: 0;
  color: #a09ab2;
  line-height: 1.7;
}

.record-preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-preview-item {
  padding: 14px 16px;
  border: 1px solid rgba(145, 120, 255, 0.1);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(253, 251, 255, 0.98), rgba(246, 240, 255, 0.96));
}

.record-preview-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.record-preview-top strong {
  font-size: 15px;
  color: #32264e;
}

.record-preview-top span {
  flex-shrink: 0;
  font-size: 12px;
  color: #968caf;
}

.record-role {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: #7b59f4;
}

.record-message {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #736b8a;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.page-footer {
  padding: 22px 0 4px;
  text-align: center;
  font-size: 14px;
  color: #9f96ba;
}

@media (max-width: 1100px) {
  .home-page {
    grid-template-columns: 1fr;
  }

  .home-sidebar {
    position: relative;
    height: auto;
  }

  .content-grid,
  .hero-card,
  .character-grid {
    grid-template-columns: 1fr;
  }

  .section-head {
    flex-direction: column;
    align-items: start;
  }
}

@media (max-width: 720px) {
  .home-main {
    padding: 18px;
  }

  .hero-card,
  .character-section,
  .side-card {
    padding: 22px;
  }

  .hero-copy h1 {
    font-size: 34px;
  }
}
</style>
