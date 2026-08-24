import { createRouter, createWebHashHistory } from 'vue-router'
import { clearAuth, getToken } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: { public: false },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 缓存最近一次 token 的校验结果（token 变化时重新校验），避免每次导航都请求
let authCache = null // { token, valid }

// 校验本地 token 是否仍被后端认可：
// 后端每次重启后实例 ID 变化，旧 token 一律 401，此时清登录态回到登录页。
async function ensureAuthValid() {
  const token = getToken()
  if (!token) return false
  if (authCache && authCache.token === token) return authCache.valid
  try {
    const res = await fetch('/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    authCache = { token, valid: res.ok }
  } catch {
    authCache = { token, valid: false }
  }
  return authCache.valid
}

// 导航守卫：未登录（或 token 已被后端判失效）访问受保护页面 → 跳转登录页
router.beforeEach(async (to) => {
  if (!to.meta.public) {
    if (!(await ensureAuthValid())) {
      clearAuth()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    return true
  }
  if (to.name === 'login' && (await ensureAuthValid())) {
    return { name: 'chat' }
  }
  return true
})

export default router
