const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const REQUEST_TIMEOUT = 8000
const AI_REQUEST_TIMEOUT = 120000

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeout || REQUEST_TIMEOUT)
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(options.timeout > REQUEST_TIMEOUT ? 'AI 响应超时，请稍后重试或换用更快的模型。' : '请求超时，请确认后端服务是否已启动。')
    }
    throw new Error('无法连接后端服务，请确认 API 地址和端口。')
  } finally {
    window.clearTimeout(timeout)
  }
  if (!response.ok) {
    let message = '请求失败'
    try {
      const data = await response.json()
      message = data.detail || message
    } catch {
      message = await response.text()
    }
    throw new Error(message)
  }
  return response.json()
}

export const assetUrl = (path) => path ? `${API_BASE}${path}` : ''

export const api = {
  health: () => request('/api/health'),
  getSettings: () => request('/api/settings'),
  saveSettings: (data) => request('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  listResumes: () => request('/api/resumes'),
  uploadResume: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/resumes', { method: 'POST', body: form })
  },
  deleteResume: (id) => request(`/api/resumes/${id}`, { method: 'DELETE' }),
  getProfile: () => request('/api/profile'),
  saveProfile: (data) => request('/api/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  }),
  exportProfile: () => request('/api/profile/export', { method: 'POST' }),
  listJds: () => request('/api/jds'),
  createJd: (data) => request('/api/jds', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    timeout: AI_REQUEST_TIMEOUT
  }),
  extractJd: (id) => request(`/api/jds/${id}/extract`, { method: 'POST', timeout: AI_REQUEST_TIMEOUT }),
  deleteJd: (id) => request(`/api/jds/${id}`, { method: 'DELETE' }),
  listInterviews: () => request('/api/interviews'),
  getInterview: (id) => request(`/api/interviews/${id}`),
  deleteInterview: (id) => request(`/api/interviews/${id}`, { method: 'DELETE' }),
  createInterview: (data) => request('/api/interviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    timeout: AI_REQUEST_TIMEOUT
  }),
  answerInterview: (id, content) => request(`/api/interviews/${id}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    timeout: AI_REQUEST_TIMEOUT
  }),
  finishInterview: (id) => request(`/api/interviews/${id}/finish`, { method: 'POST', timeout: AI_REQUEST_TIMEOUT })
}
