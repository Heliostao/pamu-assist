// Token 与用户信息的会话缓存（关闭浏览器后自动失效）
const TOKEN_KEY = 'pamu_token'
const USER_KEY = 'pamu_user'

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearAuth() {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

export function getUser() {
  const raw = sessionStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setUser(user) {
  sessionStorage.setItem(USER_KEY, JSON.stringify(user))
}
