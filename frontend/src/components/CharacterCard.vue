<script setup lang="ts">
defineProps<{
  name: string
  summary: string
  tags: string[]
  theme: 'light' | 'dark'
  selected?: boolean
}>()

const emit=defineEmits<{
  (e: 'select'): void
}>()
</script>

<template>
  <article class="character-card" :class="[theme, { selected }]">
    <div class="art-cover">
      <div class="art-glow"></div>
      <div class="art-avatar">{{ name.slice(0, 1) }}</div>
    </div>

    <h3>{{ name }}</h3>
    <p>{{ summary }}</p>

    <div class="tag-list">
      <span v-for="tag in tags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <button type="button" @click="emit('select')">{{ selected ? '已选择' : '选择TA' }}</button>
  </article>
</template>

<style scoped>
.character-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(164, 146, 234, 0.14);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 16px 50px rgba(166, 155, 214, 0.14);
}

.character-card.selected {
  border-color: rgba(134, 92, 255, 0.52);
  box-shadow: 0 22px 58px rgba(143, 109, 255, 0.18);
}

.art-cover {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  border-radius: 22px;
}

.character-card.light .art-cover {
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.92), transparent 28%),
    linear-gradient(145deg, #efe8ff, #ddd0ff 55%, #f7f2ff);
}

.character-card.dark .art-cover {
  background:
    radial-gradient(circle at 75% 30%, rgba(136, 110, 230, 0.18), transparent 22%),
    linear-gradient(160deg, #4a4660, #28263c 55%, #1a1827);
}

.art-glow {
  position: absolute;
  inset: auto -10% -20% auto;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 106, 255, 0.26), transparent 68%);
}

.art-avatar {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 144px;
  height: 144px;
  border-radius: 50%;
  font-size: 56px;
  font-weight: 700;
}

.character-card.light .art-avatar {
  color: #7151e8;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(232, 223, 255, 0.84));
  box-shadow: 0 18px 45px rgba(155, 128, 255, 0.26);
}

.character-card.dark .art-avatar {
  color: #ffffff;
  background: linear-gradient(135deg, rgba(126, 95, 229, 0.82), rgba(28, 24, 44, 0.88));
  box-shadow: 0 18px 45px rgba(24, 18, 42, 0.36);
}

.character-card h3 {
  margin: 0;
  font-size: 24px;
  color: #211638;
}

.character-card p {
  margin: 0;
  line-height: 1.7;
  color: #817695;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 6px 10px;
  font-size: 12px;
  color: #7b5de0;
  background: rgba(140, 110, 248, 0.1);
  border-radius: 999px;
}

.character-card button {
  width: 100%;
  padding: 16px 18px;
  border: none;
  border-radius: 18px;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(90deg, #8b66ff, #a888ff);
  cursor: pointer;
}
</style>
