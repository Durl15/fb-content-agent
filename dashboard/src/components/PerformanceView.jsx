import { useState, useEffect } from 'react'
import { getPerformance } from '../api.js'

function getTitle(topicStr) {
  try {
    return JSON.parse(topicStr || '{}').title || '—'
  } catch {
    return '—'
  }
}

const FORMAT_LABELS = { reel_script: 'Reel', carousel: 'Carousel', text_post: 'Text' }

export default function PerformanceView({ toast }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPerformance()
      .then(setRows)
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setLoading(false))
  }, [toast])

  if (loading) {
    return (
      <div className="loading-row">
        <span className="spinner" />
        Loading…
      </div>
    )
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">
            Performance
            <span className="count-chip">{rows.length} entries</span>
          </div>
          <div className="section-sub">Last 7 days · refreshed on page load</div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">📊</div>
          <p>No performance data yet. Post some content first.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="perf-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Format</th>
                <th>Checked</th>
                <th>Reach</th>
                <th>Views</th>
                <th>Likes</th>
                <th>Comments</th>
                <th>Shares</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {getTitle(r.topic)}
                  </td>
                  <td>
                    <span className={`badge badge-${r.format === 'reel_script' ? 'reel' : r.format === 'carousel' ? 'carousel' : 'text'}`}>
                      {FORMAT_LABELS[r.format] || r.format || '—'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {new Date(r.checked_at).toLocaleString()}
                  </td>
                  <td>{r.reach ?? 0}</td>
                  <td>{r.views ?? 0}</td>
                  <td>{r.likes ?? 0}</td>
                  <td>{r.comments ?? 0}</td>
                  <td>{r.shares ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
