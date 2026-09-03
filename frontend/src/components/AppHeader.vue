<script setup lang="ts">
defineProps<{
  title: string
  subtitle: string
}>()
</script>

<template>
  <header class="hero">
    <div class="hero-copy">
      <span class="hero-tag">Agent Playground</span>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>

      <div class="hero-actions">
        <button type="button" class="primary-btn">开始对话</button>
        <button type="button" class="secondary-btn">查看角色</button>
      </div>
    </div>

    <div class="hero-panel">
      <p class="panel-label">系统概览</p>
      <div class="panel-grid">
        <div>
          <span class="panel-value">4</span>
          <span class="panel-name">已规划模式</span>
        </div>
        <div>
          <span class="panel-value">3</span>
          <span class="panel-name">核心记忆层</span>
        </div>
        <div>
          <span class="panel-value">RAG</span>
          <span class="panel-name">知识检索</span>
        </div>
        <div>
          <span class="panel-value">Graph</span>
          <span class="panel-name">工作流调度</span>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
  gap: 24px;
  padding: 32px;
  border: 1px solid rgba(34, 29, 40, 0.08);
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(201, 120, 61, 0.18), transparent 34%),
    linear-gradient(135deg, #fff8ef 0%, #f4ede5 48%, #ece7e1 100%);
  box-shadow: 0 24px 80px rgba(32, 25, 18, 0.08);
}

.hero-copy h1 {
  margin: 14px 0 12px;
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: #1b1612;
}

.hero-copy p {
  max-width: 640px;
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  color: #5b534b;
}

.hero-tag {
  display: inline-flex;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7e4b17;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(126, 75, 23, 0.12);
  border-radius: 999px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}

.primary-btn,
.secondary-btn {
  padding: 14px 20px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn {
  color: #fff8ef;
  background: linear-gradient(135deg, #2d2430, #17121c);
  border: none;
}

.secondary-btn {
  color: #2d2430;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(34, 29, 40, 0.12);
}

.hero-panel {
  padding: 24px;
  border-radius: 28px;
  color: #f6f2ea;
  background: linear-gradient(180deg, #26212d, #16131c);
}

.panel-label {
  margin: 0 0 18px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(246, 242, 234, 0.62);
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel-grid div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
}

.panel-value {
  font-size: 24px;
  font-weight: 700;
}

.panel-name {
  font-size: 12px;
  color: rgba(246, 242, 234, 0.62);
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 24px;
  }
}
</style>
