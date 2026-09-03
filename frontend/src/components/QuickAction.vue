<script setup lang="ts">
defineProps<{
  title: string
  description: string
  badge: string
}>()
</script>

<template>
  <article class="quick-card">
    <span class="quick-badge">{{ badge }}</span>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <button type="button">进入模块</button>
  </article>
</template>

<style scoped>
.quick-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  min-height: 220px;
  border: 1px solid rgba(38, 33, 45, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 40px rgba(26, 20, 15, 0.06);
}

.quick-badge {
  display: inline-flex;
  align-self: flex-start;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #89511f;
  background: rgba(240, 204, 154, 0.32);
  border-radius: 999px;
}

.quick-card h3 {
  margin: 0;
  font-size: 20px;
  color: #1d1713;
}

.quick-card p {
  flex: 1;
  margin: 0;
  line-height: 1.7;
  color: #655d55;
}

.quick-card button {
  align-self: flex-start;
  padding: 12px 16px;
  border: 1px solid rgba(38, 33, 45, 0.12);
  border-radius: 14px;
  color: #2b242f;
  background: transparent;
  cursor: pointer;
}
</style>
