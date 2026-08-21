import axios from 'axios'
import { clearAuth, getToken } from '../stores/auth'
import router from '../router'

// 统一的 HTTP 客户端：接口地址只在此处配置，页面组件不出现具体路径
const http = axios.create({
  baseURL: '',
  timeout: 30000,
})

// 请求拦截：自动携带 token
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 时清除本地登录态并跳转登录页
http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      clearAuth()
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }
    return Promise.reject(err)
  },
)

export default http
