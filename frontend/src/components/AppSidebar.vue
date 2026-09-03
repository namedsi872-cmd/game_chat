<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  activePage?: 'home' | 'records'
}>()

const emit = defineEmits<{
  (e: 'login'): void
  (e: 'go-home'): void
  (e: 'go-records'): void
}>()

const navItems = computed(() => [
  {
    key: 'home',
    label: '首页',
    icon: '⌂',
    active: props.activePage === 'home',
    action: () => emit('go-home'),
  },
  {
    key: 'characters',
    label: '角色选择',
    icon: '◈',
    active: false,
    action: () => emit('go-home'),
  },
  {
    key: 'records',
    label: '陪玩记录',
    icon: '☰',
    active: props.activePage === 'records',
    action: () => emit('go-records'),
  },
  {
    key: 'profile',
    label: '个人中心',
    icon: '◎',
    active: false,
    action: () => {},
  },
  {
    key: 'settings',
    label: '设置',
    icon: '⚙',
    active: false,
    action: () => {},
  },
])
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">PA</div>
      <div>
        <p class="brand-title">陪玩智能体</p>
        <p class="brand-subtitle">PLAY AI</p>
      </div>
    </div>

    <nav class="nav">
      <button
        v-for="item in navItems"
        :key="item.key"
        type="button"
        class="nav-item"
        :class="{ active: item.active }"
        @click="item.action"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <button type="button" class="login-entry" @click="emit('login')">
      <span class="login-avatar">◉</span>
      <div>
        <p class="login-title">登录</p>
        <p class="login-subtitle">点击后接入你的登录逻辑</p>
      </div>
    </button>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 28px;
  min-height: 100%;
  padding: 30px 20px;
  color: #2d2140;
  background: rgba(255, 255, 255, 0.46);
  backdrop-filter: blur(14px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #8c63ff, #6f4df4);
  box-shadow: 0 16px 34px rgba(124, 92, 255, 0.28);
}

.brand-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #22173c;
}

.brand-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: rgba(109, 87, 188, 0.7);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 18px;
  text-align: left;
  color: #756f8e;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 22px;
  cursor: pointer;
  transition: transform 0.2s ease, color 0.2s ease, background 0.2s ease;
}

.nav-item:hover,
.nav-item.active {
  transform: translateX(2px);
  color: #784ef7;
  background: rgba(139, 106, 255, 0.12);
}

.nav-icon {
  display: grid;
  place-items: center;
  width: 28px;
  font-size: 18px;
  color: currentColor;
}

.nav-label {
  font-size: 24px;
  font-weight: 600;
}

.login-entry {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  color: #5b477e;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(244, 238, 255, 0.96));
  border: 1px solid rgba(140, 117, 255, 0.12);
  border-radius: 22px;
  box-shadow: 0 16px 40px rgba(164, 146, 234, 0.18);
  cursor: pointer;
}

.login-avatar {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #8b67ff, #b48cff);
}

.login-title {
  margin: 0;
  font-weight: 600;
  color: #3d2a62;
}

.login-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(82, 68, 122, 0.66);
}
</style>
