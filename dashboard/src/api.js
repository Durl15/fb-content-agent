const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    let msg = `${res.status} error`
    try {
      const j = await res.json()
      msg = j.detail || j.message || msg
    } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const listContent = (status = '', limit = 50) => {
  const params = new URLSearchParams({ limit })
  if (status) params.set('status', status)
  return request(`/content?${params}`)
}

export const getContent = (id) => request(`/content/${id}`)

export const generateContent = (count = 10) =>
  request('/content/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count }),
  })

export const scheduleContent = (id, scheduled_time) =>
  request(`/content/${id}/schedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scheduled_time }),
  })

export const postNow = (id) =>
  request(`/content/${id}/post-now`, { method: 'POST' })

export const getPerformance = () => request('/performance')

export const getReport = () => request('/report')

export const getTokenStatus = () => request('/token-status')

export const refreshToken = () => request('/token-refresh', { method: 'POST' })
