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
  extractResumeText: (id) => request(`/api/resumes/${id}/extract-text`, { method: 'POST', timeout: AI_REQUEST_TIMEOUT }),
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
  extractJdFromUrl: (url) => request('/api/jds/extract-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    timeout: AI_REQUEST_TIMEOUT
  }),
  updateJd: (id, data) => request(`/api/jds/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
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
  answerInterviewStream: async (id, content, onDelta) => {
    const response = await fetch(`${API_BASE}/api/interviews/${id}/answer/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    })
    if (!response.ok || !response.body) {
      return request(`/api/interviews/${id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        timeout: AI_REQUEST_TIMEOUT
      })
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalInterview = null
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.trim()) continue
        const event = JSON.parse(line)
        if (event.type === 'delta') onDelta?.(event.content)
        if (event.type === 'done') finalInterview = event.interview
      }
    }
    if (buffer.trim()) {
      const event = JSON.parse(buffer)
      if (event.type === 'delta') onDelta?.(event.content)
      if (event.type === 'done') finalInterview = event.interview
    }
    return finalInterview || api.getInterview(id)
  },
  finishInterview: (id) => request(`/api/interviews/${id}/finish`, { method: 'POST', timeout: AI_REQUEST_TIMEOUT })
}
