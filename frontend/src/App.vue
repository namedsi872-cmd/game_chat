<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import ChatPanel from './components/ChatPanel.vue'
import LoginResister from './components/LoginResister.vue'
import HomeView from './views/HomeView.vue'
import RecordsView from './views/RecordsView.vue'

const isMiniMode = new URLSearchParams(window.location.search).get('mini') === '1'
const savedUserId = window.localStorage.getItem('userId')
const savedUsername = window.localStorage.getItem('username')
const hasSavedLogin = !!savedUserId && !!savedUsername

const userId = ref<number | undefined>(hasSavedLogin ? Number(savedUserId) : undefined)
const username = ref(hasSavedLogin ? savedUsername : '')

const showlogin = ref(isMiniMode && !hasSavedLogin)
const currentPage = ref<'home' | 'chat' | 'records'>(isMiniMode ? 'chat' : 'home')
const roleName = ref('yagami_light')
const gameName = ref('')

onMounted(() => {
  if (!isMiniMode) return

  document.documentElement.style.background = 'transparent'
  document.body.style.background = 'transparent'
})

onBeforeUnmount(() => {
  if (!isMiniMode) return

  document.documentElement.style.background = ''
  document.body.style.background = ''
})

const loginSuccess = (payload: { userId: number; username: string }) => {
  userId.value = payload.userId
  username.value = payload.username
  showlogin.value = false
  window.localStorage.setItem('userId', String(payload.userId))
  window.localStorage.setItem('username', payload.username)
}

const openLogin = () => {
  showlogin.value = true
}

const handleStartPlay = async () => {
  if (!userId.value) {
    showlogin.value = true
    return
  }

  currentPage.value = 'chat'
}

const handleRoleChange = (newRoleName: string) => {
  roleName.value = newRoleName
}

const handleGameChange = (newGameName: string) => {
  gameName.value = newGameName
}

const goHome = () => {
  if (isMiniMode) {
    currentPage.value = 'chat'
    return
  }

  currentPage.value = 'home'
}

const goRecords = () => {
  if (!userId.value) {
    showlogin.value = true
    return
  }

  currentPage.value = 'records'
}
</script>

<template>
  <HomeView
    v-if="currentPage === 'home'"
    :userId="userId"
    :username="username"
    :roleName="roleName"
    :gameName="gameName"
    @login="openLogin"
    @start_Play="handleStartPlay"
    @change_role="handleRoleChange"
    @change_game="handleGameChange"
    @go-records="goRecords"
  />

  <RecordsView
    v-else-if="currentPage === 'records'"
    :userId="userId"
    :username="username"
    @login="openLogin"
    @go-home="goHome"
    @start-play="handleStartPlay"
  />

  <ChatPanel
    v-else
    :userId="userId"
    :roleName="roleName"
    :gameName="gameName"
    @go-home="goHome"
    @change-game="handleGameChange"
  />

  <div v-if="showlogin" class="login-mask">
    <div class="login-dialog">
      <LoginResister @loginSuccess="loginSuccess" />
    </div>
  </div>
</template>

<style scoped>
.login-mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(22, 16, 40, 0.45);
  backdrop-filter: blur(6px);
  z-index: 999;
}

.login-dialog {
  width: min(420px, 90vw);
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 80px rgba(48, 32, 96, 0.25);
}
</style>
