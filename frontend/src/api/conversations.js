import http from './http'

// 会话列表
export function listConversations() {
  return http.get('/conversations')
}

// 新建会话
export function createConversation(title = '新对话') {
  return http.post('/conversations', { title })
}

// 删除会话
export function deleteConversation(id) {
  return http.delete(`/conversations/${id}`)
}

// 会话消息列表
export function listMessages(id) {
  return http.get(`/conversations/${id}/messages`)
}
