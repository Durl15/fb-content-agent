import { useState, useEffect, useCallback } from 'react'
import { listContent, generateContent } from '../api.js'
import ContentCard from './ContentCard.jsx'

const STATUSES = ['', 'draft', 'scheduled', 'posted']
const STATUS_LABELS = { '': 'All', draft: 'Draft', scheduled: 'Scheduled', posted: 'Posted' }

export default function ContentList({ toast }) {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [count, setCount] = useState(10)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listContent(status)
      setItems(data)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [status, toast])

  useEffect(() => { load() }, [load])

  async function handleGenerate() {
    setGenerating(true)
    try {
      const res = await generateContent(count)
      toast(`Generated ${res.generated} drafts`)
      await load()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">
            Content
            <span className="count-chip">{items.length}</span>
          </div>
          <div className="section-sub">Manage and publish your content pipeline</div>
        </div>
      </div>

      <div className="toolbar">
        <div className="filter-tabs">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`filter-btn ${status === s ? 'active' : ''}`}
              onClick={() => setStatus(s)}
            >
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
        <div className="spacer" />
        <input
          type="number"
          min={1}
          max={50}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
          style={{
            width: 60,
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text)',
            padding: '6px 8px',
            fontSize: 13,
          }}
          title="Number of posts to generate"
        />
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? (
            <>
              <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              Generating…
            </>
          ) : (
            '+ Generate'
          )}
        </button>
      </div>

      {loading ? (
        <div className="loading-row">
          <span className="spinner" />
          Loading…
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">📭</div>
          <p>No {status || ''} content yet.</p>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            Generate content
          </button>
        </div>
      ) : (
        <div className="content-grid">
          {items.map((item) => (
            <ContentCard
              key={item.id}
              item={item}
              onRefresh={load}
              toast={toast}
            />
          ))}
        </div>
      )}
    </>
  )
}
