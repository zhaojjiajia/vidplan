<template>
  <div class="auth">
    <main class="main">
      <div class="form-wrap">
        <h1 class="auth-title">登录</h1>

        <el-form :model="form" label-position="top" @submit.prevent="onSubmit" class="form">
          <el-form-item label="用户名">
            <el-input v-model="form.username" autocomplete="username" size="large" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" autocomplete="current-password" size="large" placeholder="请输入密码" />
          </el-form-item>
          <el-button type="primary" :loading="loading" native-type="submit" size="large" class="submit">登录</el-button>
        </el-form>

        <div class="hint">
          没有账号?<router-link to="/register">立即注册</router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    const redirect = (route.query.redirect as string) || '/app/me/plans'
    router.push(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth {
  min-height: 100vh;
  background: transparent;
}

/* ----- 表单 ----- */
.main {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.form-wrap {
  width: 100%;
  max-width: 420px;
  padding: 30px 34px 28px;
  border: none;
  border-radius: var(--vp-r-lg);
  background: color-mix(in srgb, var(--vp-surface) 62%, transparent);
  box-shadow: 0 24px 72px rgba(84, 40, 36, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.46);
  backdrop-filter: blur(18px) saturate(142%);
}
.auth-title {
  margin-bottom: 24px;
  font-size: 32px;
  line-height: 1.18;
  text-align: center;
  color: var(--vp-text-1);
  text-shadow: 0 1px 3px rgba(255, 255, 255, 0.78);
  white-space: nowrap;
}
.form { display: flex; flex-direction: column; gap: 4px; }
.submit { width: 100%; margin-top: 8px; height: 48px; font-weight: 500; font-size: 17px; }
.hint { margin-top: 22px; text-align: center; color: var(--vp-text-3); font-size: 16px; }
.hint a { color: var(--vp-primary); text-decoration: none; font-weight: 500; }
.hint a:hover { text-decoration: underline; }

@media (max-width: 880px) {
  .main { padding: 20px; }
  .form-wrap { padding: 28px 22px 24px; }
  .auth-title { font-size: 28px; white-space: normal; }
}
</style>
