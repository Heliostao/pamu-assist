<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createConversation, deleteConversation, listConversations, listMessages } from '../api/conversations'
import { clearAuth, getToken, getUser } from '../stores/auth'

const router = useRouter()

const messages = ref([]) // { role, content }
const conversations = ref([])
const currentConvId = ref(null)
const inputText = ref('')
const sending = ref(false)
const loadingHistory = ref(false)
const messageListEl = ref(null)
const user = ref(getUser())
const isMobile = ref(window.innerWidth < 768)
const sidebarOpen = ref(window.innerWidth >= 768)

const emptyConversations = computed(() => conversations.value.length === 0)

async function refreshConversations() {
  try {
    const res = await listConversations()
    conversations.value = res.data
  } catch {
    // 401 已由拦截器统一处理
  }
}

async function newConversation() {
  try {
    const res = await createConversation()
    currentConvId.value = res.data.id
    messages.value = []
    await refreshConversations()
    scrollDown()
  } catch {
    /* 忽略 */
  }
}

async function openConversation(id) {
  if (id === currentConvId.value) return
  currentConvId.value = id
  loadingHistory.value = true
  messages.value = []
  try {
    const res = await listMessages(id)
    messages.value = res.data.map((m) => ({ role: m.role, content: m.content }))
    await nextTick()
    scrollDown()
  } finally {
    loadingHistory.value = false
  }
}

async function removeConversation(id) {
  if (!confirm('确定删除这个对话吗？')) return
  try {
    await deleteConversation(id)
    if (currentConvId.value === id) {
      currentConvId.value = null
      messages.value = []
    }
    await refreshConversations()
  } catch {
    /* 忽略 */
  }
}

function logout() {
  clearAuth()
  router.push({ name: 'login' })
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function handleResize() {
  isMobile.value = window.innerWidth < 768
  // 跨断点时自动复位：桌面展开、移动收起
  sidebarOpen.value = !isMobile.value
}

function scrollDown() {
  if (messageListEl.value) {
    messageListEl.value.scrollTop = messageListEl.value.scrollHeight
  }
}

async function send() {
  const question = inputText.value.trim()
  if (!question || sending.value) return

  // 首次发送时自动创建会话
  if (currentConvId.value === null) {
    try {
      const res = await createConversation()
      currentConvId.value = res.data.id
      await refreshConversations()
    } catch {
      return
    }
  }

  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  sending.value = true
  scrollDown()

  // 占位 AI 消息（流式填充）
  messages.value.push({ role: 'assistant', content: '' })
  const aiIndex = messages.value.length - 1
  scrollDown()

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ question, conversation_id: currentConvId.value }),
    })

    if (res.status === 401) {
      clearAuth()
      router.push({ name: 'login' })
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        if (payload === '[DONE]') continue
        try {
          const parsed = JSON.parse(payload)
          if (parsed.t) {
            messages.value[aiIndex].content += parsed.t
            scrollDown()
          }
          if (parsed.error) {
            messages.value[aiIndex].content =
              (messages.value[aiIndex].content || '') + `\n[错误] ${parsed.error}`
          }
        } catch {
          /* 跳过非 JSON 行 */
        }
      }
    }

    if (!messages.value[aiIndex].content) {
      messages.value[aiIndex].content = '(帕姆一时语塞，请再问我一次帕…)'
    }
    await refreshConversations()
  } catch {
    messages.value[aiIndex].content = '网络出了点问题，请稍后再试帕…'
  } finally {
    sending.value = false
    scrollDown()
  }
}

onMounted(() => {
  refreshConversations()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div class="layout">
    <!-- 移动端抽屉遮罩 -->
    <div v-if="isMobile && sidebarOpen" class="sidebar-mask" @click="sidebarOpen = false"></div>

    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-brand">
        <span class="brand-dot"></span>
        <span class="brand-name">帕姆帮帮</span>
      </div>

      <button class="btn-primary new-btn" @click="newConversation">+ 新建对话</button>

      <div class="conv-list">
        <p v-if="emptyConversations" class="conv-empty">暂无历史对话</p>
        <div
          v-for="c in conversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === currentConvId }"
          @click="openConversation(c.id)"
        >
          <span class="conv-title">{{ c.title }}</span>
          <button class="conv-del" title="删除" @click.stop="removeConversation(c.id)">×</button>
        </div>
      </div>

      <div class="sidebar-user">
        <div class="user-mail">{{ user?.nickname || user?.username || user?.email || '未知用户' }}</div>
        <button class="btn-secondary logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="main">
      <header class="topbar">
        <button class="icon-btn" title="展开/收起侧边栏" @click="toggleSidebar">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <span class="topbar-title">帕姆帮帮</span>
      </header>
      <div ref="messageListEl" class="messages">
        <div v-if="messages.length === 0" class="empty-state">
          <h1 class="greeting">你好，<span class="greeting-right">开拓者</span></h1>
          <p>我是帕姆，列车组的列车长！你可以问我任何关于崩坏：星穹铁道角色的问题帕。</p>
        </div>

        <div v-if="loadingHistory" class="msg msg-ai">
          <div class="role-label">帕姆</div>
          <div class="msg-loading"><span>正在翻阅智库</span></div>
        </div>

        <div
          v-for="(m, i) in messages"
          :key="i"
          class="msg"
          :class="m.role === 'user' ? 'msg-user' : 'msg-ai'"
        >
          <template v-if="m.role === 'assistant'">
            <div class="role-label">帕姆</div>
            <div class="stream-text">{{ m.content }}</div>
          </template>
          <template v-else>{{ m.content }}</template>
        </div>
      </div>

      <div class="input-bar">
        <form class="input-row" @submit.prevent="send">
          <input
            v-model="inputText"
            type="text"
            placeholder="询问任意星穹铁道角色信息…"
            :disabled="sending"
          />
          <button type="submit" :disabled="sending">{{ sending ? '思考中…' : '发送' }}</button>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface-dark);
  color: var(--on-dark);
  padding: 20px 16px;
  transition: margin-left 0.25s ease, transform 0.25s ease;
}

/* 移动端抽屉遮罩 */
.sidebar-mask {
  position: fixed;
  inset: 0;
  background: rgba(20, 20, 19, 0.45);
  z-index: 90;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 0 4px;
}

.brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary);
}

.brand-name {
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--on-dark);
}

.new-btn {
  width: 100%;
  margin-bottom: 16px;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conv-empty {
  color: var(--on-dark-soft);
  font-size: 13px;
  text-align: center;
  padding: 24px 0;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--rounded-md);
  cursor: pointer;
  transition: background 0.15s ease;
}

.conv-item:hover {
  background: var(--surface-dark-elevated);
}

.conv-item.active {
  background: var(--surface-dark-elevated);
  color: var(--on-dark);
}

.conv-title {
  flex: 1;
  font-size: 14px;
  color: var(--on-dark-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-item.active .conv-title {
  color: var(--on-dark);
}

.conv-del {
  border: none;
  background: transparent;
  color: var(--on-dark-soft);
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.conv-item:hover .conv-del {
  opacity: 1;
}

.conv-del:hover {
  color: var(--error);
}

.sidebar-user {
  border-top: 1px solid var(--surface-dark-elevated);
  padding-top: 16px;
  margin-top: 12px;
}

.user-mail {
  font-size: 13px;
  color: var(--on-dark-soft);
  margin-bottom: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logout-btn {
  width: 100%;
  height: 36px;
  background: var(--surface-dark-elevated);
  color: var(--on-dark);
  border: 1px solid var(--surface-dark-elevated);
}

.logout-btn:hover {
  background: var(--surface-dark-soft);
}

/* ── 主聊天区 ── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 顶部工具条 */
.topbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 14px;
  background: var(--canvas);
  border-bottom: 1px solid var(--hairline);
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--rounded-md);
  color: var(--muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.icon-btn:hover {
  background: var(--surface-soft);
  color: var(--ink);
}

.topbar-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px 24px;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
}

.empty-state {
  text-align: center;
  padding: 80px 0 0;
}

.greeting {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 400;
  letter-spacing: -0.5px;
  color: var(--ink);
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 16px;
  color: var(--muted);
  max-width: 400px;
  margin: 0 auto;
}

.msg {
  max-width: 85%;
  margin-bottom: 20px;
}

.msg-user {
  margin-left: auto;
  background: var(--surface-card);
  color: var(--ink);
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 15px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.msg-ai {
  margin-right: auto;
  background: var(--surface-dark);
  color: var(--on-dark);
  border-radius: 12px;
  padding: 18px 22px;
  font-size: 15px;
  line-height: 1.6;
  max-width: 85%;
}

.msg-ai .role-label {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--on-dark-soft);
  margin-bottom: 8px;
}

.stream-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--on-dark-soft);
}

/* ── 输入区 ── */
.input-bar {
  border-top: 1px solid var(--hairline);
  background: var(--canvas);
  padding: 16px 24px 24px;
}

.input-row {
  display: flex;
  gap: 10px;
  max-width: 720px;
  margin: 0 auto;
}

.input-row input {
  flex: 1;
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--ink);
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: 10px 14px;
  height: 40px;
  outline: none;
  transition: border-color 0.15s;
}

.input-row input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(204, 120, 92, 0.15);
}

.input-row input:disabled {
  background: var(--surface-soft);
  color: var(--muted);
}

.input-row input::placeholder {
  color: var(--muted-soft);
}

.input-row button {
  font-size: 14px;
  font-weight: 500;
  color: var(--on-primary);
  background: var(--primary);
  border: none;
  border-radius: 8px;
  padding: 0 20px;
  height: 40px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.input-row button:hover {
  background: var(--primary-active);
}

.input-row button:disabled {
  background: var(--primary-disabled);
  color: var(--muted);
  cursor: not-allowed;
}

/* ── 响应式 ── */
/* 桌面端：侧边栏可收起（负边距移出，主区自动占满） */
@media (min-width: 768px) {
  .sidebar:not(.open) {
    margin-left: -260px;
  }
}

/* 移动端：侧边栏变为抽屉，默认收起 */
@media (max-width: 767px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 100;
    margin-left: 0;
    transform: translateX(-100%);
  }

  .sidebar.open {
    transform: translateX(0);
    box-shadow: 0 0 30px rgba(0, 0, 0, 0.4);
  }

  .messages {
    padding: 16px 14px;
  }

  .msg,
  .msg-ai {
    max-width: 92%;
  }

  .greeting {
    font-size: 28px;
  }

  .input-bar {
    padding: 10px 12px 16px;
  }
}
</style>
