import { useState, useEffect } from 'react'
import { getTokenStatus, refreshToken } from '../api.js'

export default function TokenBanner() {
  const [status, setStatus] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    getTokenStatus().then(setStatus).catch(() => null)
  }, [])

  if (!status) return null

  const { valid, days_remaining, expires_at } = status

  // Non-expiring valid token — show nothing
  if (valid && expires_at === null) return null
  // Healthy token with plenty of time — show nothing
  if (valid && days_remaining !== null && days_remaining >= 7) return null

  const expired = !valid || (days_remaining !== null && days_remaining <= 0)
  const bg = expired ? 'rgba(239,68,68,0.12)' : 'rgba(234,179,8,0.12)'
  const border = expired ? 'rgba(239,68,68,0.35)' : 'rgba(234,179,8,0.35)'
  const color = expired ? 'var(--red)' : 'var(--yellow)'

  const label = expired
    ? 'FB access token has expired — posts will fail'
    : `FB access token expires in ${days_remaining} day${days_remaining === 1 ? '' : 's'}`

  async function handleRefresh() {
    setRefreshing(true)
    setMessage(null)
    try {
      await refreshToken()
      const fresh = await getTokenStatus()
      setStatus(fresh)
      setMessage('Token refreshed successfully')
    } catch (e) {
      setMessage(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      color,
      padding: '8px 24px',
      fontSize: 13,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontWeight: 500,
    }}>
      <span>⚠ {label}</span>
      {expires_at && (
        <span style={{ fontWeight: 400, opacity: 0.75 }}>
          ({new Date(expires_at).toLocaleDateString()})
        </span>
      )}
      <button
        onClick={handleRefresh}
        disabled={refreshing}
        style={{
          marginLeft: 'auto',
          background: 'none',
          border: `1px solid ${color}`,
          color,
          borderRadius: 5,
          padding: '3px 10px',
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 600,
          opacity: refreshing ? 0.5 : 1,
        }}
      >
        {refreshing ? 'Refreshing…' : 'Auto-Refresh'}
      </button>
      {message && (
        <span style={{ fontSize: 12, opacity: 0.85 }}>{message}</span>
      )}
    </div>
  )
}
