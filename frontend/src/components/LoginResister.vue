<script setup lang="ts">
import { ref } from 'vue'
const password = ref('')
const username = ref('')


const userId = ref<number | null>(null)

const emit = defineEmits(['loginSuccess'])
const handellogin = async() => {
  const resonse=await fetch('http://127.0.0.1:8000/login',{
    method:'POST',
    headers:{
      'Content-Type':'application/json'
    },
    body:JSON.stringify({
      username:username.value,
      password:password.value
    })
  })
  const data=await resonse.json()
  userId.value=data.user_id
 
  emit('loginSuccess', {
    userId:userId.value,
    username:username.value})
  

  alert(userId.value)
  
  localStorage.setItem('userId',data.user_id)
  localStorage.setItem('username',username.value)
  
  alert('登录成功')

}
// 把userid传递给chatpanel

</script>

<template>
  <div>
    <h1>Login Resister</h1>
    <p>This is a simple login resister.</p>
  </div>

  <div>
    登录
    <input type="text" v-model="username" placeholder="请输入用户名">
    <input type="password" v-model="password" placeholder="请输入密码">
    <button  @click="handellogin()">登录</button>

  </div>
  <div>
      <h2>当前状态</h2>

      <p>userId: {{ userId }}</p>
    </div>
</template>

<style scoped>
div {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
}

h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

p {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

input {
  width: 100%;
  max-width: 300px;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

button {
  width: 100%;
  max-width: 300px;
  padding: 12px;
  background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}

button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(139, 92, 246, 0.4);
}

h2 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}
</style>
