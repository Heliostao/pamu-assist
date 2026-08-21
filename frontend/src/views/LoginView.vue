<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loginByEmail, loginByPassword, sendVcode } from '../api/auth'
import { setToken, setUser } from '../stores/auth'

const router = useRouter()
const route = useRoute()

const mode = ref('password') // password | vcode
const loading = ref(false)
const errorMsg = ref('')
const countdown = ref(0)
let timer = null

const form = reactive({
  username: '',
  email: '',
  password: '',
  vcode: '',
})

const emailValid = computed(() => /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/.test(form.email.trim()))

const canSubmit = computed(() => {
  if (mode.value === 'password') {
    return form.username.trim().length > 0 && form.password.length >= 6
  }
  return emailValid.value && form.vcode.length === 6
})

function startCountdown() {
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}

async function handleSendVcode() {
  if (!emailValid.value) {
    errorMsg.value = '请输入正确的邮箱地址'
    return
  }
  if (countdown.value > 0) return
  loading.value = true
  errorMsg.value = ''
  try {
    await sendVcode(form.email.trim())
    startCountdown()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '验证码发送失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!canSubmit.value || loading.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    const res =
      mode.value === 'password'
        ? await loginByPassword(form.username.trim(), form.password)
        : await loginByEmail(form.email.trim(), form.vcode)
    setToken(res.data.token)
    setUser(res.data.user)
    router.push(route.query.redirect || '/')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <span class="brand-dot"></span>
        <h1 class="brand-title">帕姆小助手</h1>
        <h2 class="greeting animate-greeting">
          <span class="greeting-left">你好，</span><span class="greeting-right">开拓者</span>
        </h2>
        <p class="brand-sub">我是帕姆，列车组的列车长！登录后即可向我提问崩坏：星穹铁道的任何问题帕。</p>
      </div>

      <div class="tabs">
        <button
          class="tab"
          :class="{ active: mode === 'password' }"
          @click="mode = 'password'; errorMsg = ''"
        >
          账号登录
        </button>
        <button
          class="tab"
          :class="{ active: mode === 'vcode' }"
          @click="mode = 'vcode'; errorMsg = ''"
        >
          邮箱验证码
        </button>
      </div>

      <form class="form" @submit.prevent="handleSubmit">
        <template v-if="mode === 'password'">
          <label class="field">
            <span class="label">账号</span>
            <input
              v-model.trim="form.username"
              class="text-input"
              type="text"
              placeholder="请输入账号"
              autocomplete="username"
            />
          </label>

          <label class="field">
            <span class="label">密码</span>
            <input
              v-model="form.password"
              class="text-input"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </label>
        </template>

        <template v-else>
          <label class="field">
            <span class="label">邮箱</span>
            <input
              v-model.trim="form.email"
              class="text-input"
              type="email"
              placeholder="请输入邮箱"
              autocomplete="email"
            />
          </label>

          <label class="field">
            <span class="label">验证码</span>
            <div class="vcode-row">
              <input
                v-model="form.vcode"
                class="text-input vcode-input"
                type="text"
                maxlength="6"
                placeholder="6 位验证码"
              />
              <button
                type="button"
                class="btn-secondary vcode-btn"
                :disabled="countdown > 0 || loading"
                @click="handleSendVcode"
              >
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </label>
        </template>

        <p class="error-text">{{ errorMsg }}</p>

        <button class="btn-primary submit" type="submit" :disabled="!canSubmit || loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>

        <p class="hint">
          {{ mode === 'password' ? '账号登录需使用管理员分配的账号' : '验证码登录：未注册邮箱将自动创建账号' }}
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--canvas);
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--rounded-lg);
  padding: 40px 36px;
}

.brand {
  text-align: center;
  margin-bottom: 28px;
}

.brand-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary);
  margin-bottom: 12px;
}

.brand-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 500;
  letter-spacing: -0.3px;
  color: var(--ink);
}

/* 动态文字：左右滑入（复刻旧版帕姆页面的欢迎语效果） */
.greeting {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 400;
  letter-spacing: -0.3px;
  color: var(--ink);
  margin-top: 14px;
}

.animate-greeting .greeting-left,
.animate-greeting .greeting-right {
  display: inline-block;
  animation-duration: 0.6s;
  animation-timing-function: cubic-bezier(0.25, 1, 0.5, 1);
  animation-fill-mode: both;
}

.animate-greeting .greeting-left {
  animation-name: slideFromLeft;
}

.animate-greeting .greeting-right {
  animation-name: slideFromRight;
  animation-delay: 0.15s;
}

@keyframes slideFromLeft {
  from {
    opacity: 0;
    transform: translateX(-24px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideFromRight {
  from {
    opacity: 0;
    transform: translateX(24px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 缓慢浮现的那一行字（复刻旧版 fadeInGradually 效果） */
.brand-sub {
  color: var(--muted);
  font-size: 14px;
  margin-top: 10px;
  line-height: 1.6;
  opacity: 0;
  animation: fadeInGradually 1.5s ease 0.5s forwards;
}

@keyframes fadeInGradually {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tabs {
  display: flex;
  background: var(--surface-soft);
  border-radius: var(--rounded-md);
  padding: 4px;
  margin-bottom: 24px;
}

.tab {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 0;
  border-radius: var(--rounded-sm);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.tab.active {
  background: var(--canvas);
  color: var(--ink);
  box-shadow: var(--shadow-soft);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 13px;
  font-weight: 500;
  color: var(--body-strong, var(--body));
}

.vcode-row {
  display: flex;
  gap: 8px;
}

.vcode-input {
  flex: 1;
}

.vcode-btn {
  min-width: 108px;
  white-space: nowrap;
}

.submit {
  width: 100%;
  margin-top: 4px;
}

.hint {
  text-align: center;
  font-size: 12px;
  color: var(--muted-soft);
}
</style>
