import http from './http'

// 发送邮箱验证码
export function sendVcode(email) {
  return http.post('/auth/vcode', { email })
}

// 账号注册（账号 + 用户名 + 密码 + 邮箱 + 验证码，注册即绑定邮箱）
export function registerUser({ username, nickname, password, email, vcode }) {
  return http.post('/auth/register', { username, nickname, password, email, vcode })
}

// 邮箱验证码登录（仅限已绑定账号的邮箱）
export function loginByEmail(email, vcode) {
  return http.post('/auth/login/email', { email, vcode })
}

// 账号或邮箱 + 密码登录
export function loginByPassword(username, password) {
  return http.post('/auth/login/password', { username, password })
}

// 获取当前用户信息
export function fetchMe() {
  return http.get('/auth/me')
}
