import http from './http'

// 发送邮箱验证码
export function sendVcode(email) {
  return http.post('/auth/vcode', { email })
}

// 邮箱验证码登录（无账号自动注册）
export function loginByEmail(email, vcode) {
  return http.post('/auth/login/email', { email, vcode })
}

// 默认账号密码登录
export function loginByPassword(username, password) {
  return http.post('/auth/login/password', { username, password })
}

// 获取当前用户信息
export function fetchMe() {
  return http.get('/auth/me')
}
