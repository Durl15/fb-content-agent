import { useState } from 'react'
import { scheduleContent, postNow } from '../api.js'

const FORMAT_LABELS = {
  reel_script: 'Reel',
  carousel: 'Carousel',
  text_post: 'Text',
}

function formatBadgeClass(fmt) {
  if (fmt === 'reel_script') return 'badge badge-reel'
  if (fmt === 'carousel') return 'badge badge-carousel'
  return 'badge badge-text'
}

function statusBadgeClass(status) {
  return `badge badge-${status}`
}

function getPreview(item) {
  try {
    const c = JSON.parse(item.content_json || '{}')
    if (item.format === 'reel_script') return c.hook || c.caption || ''
    if (item.format === 'carousel') return c.slides?.[0]?.headline || c.caption || ''
    return c.post_text || ''
  } catch {
    return ''
  }
}

function getTitle(item) {
  try {
    const t = JSON.parse(item.topic || '{}')
    return t.title || `#${item.id}`
  } catch {
    return `#${item.id}`
  }
}

function toLocalDatetimeValue(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function ContentCard({ item, onRefresh, toast }) {
  const [scheduling, setScheduling] = useState(false)
  const [scheduleTime, setScheduleTime] = useState(
    item.scheduled_time ? toLocalDatetimeValue(item.scheduled_time) : ''
  )
  const [posting, setPosting] = useState(false)
  const [showScheduler, setShowScheduler] = useState(false)
  const [confirmPost, setConfirmPost] = useState(false)

  async function handleSchedule() {
    if (!scheduleTime) return
    setScheduling(true)
    try {
      const iso = new Date(scheduleTime).toISOString()
      await scheduleContent(item.id, iso)
      toast(`Scheduled post #${item.id}`)
      setShowScheduler(false)
      onRefresh()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setScheduling(false)
    }
  }

  async function handlePostNow() {
    setPosting(true)
    setConfirmPost(false)
    try {
      const res = await postNow(item.id)
      toast(`Posted! FB ID: ${res.fb_post_id}`)
      onRefresh()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setPosting(false)
    }
  }

  const preview = getPreview(item)
  const title = getTitle(item)

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <div className="badges">
          <span className={formatBadgeClass(item.format)}>
            {FORMAT_LABELS[item.format] || item.format}
          </span>
          <span className={statusBadgeClass(item.status)}>{item.status}</span>
        </div>
      </div>

      {preview && (
        <div className="card-preview">{preview}</div>
      )}

      {item.scheduled_time && (
        <div className="card-meta">
          Scheduled: {new Date(item.scheduled_time).toLocaleString()}
        </div>
      )}

      {item.status === 'posted' && (
        <div className="stats-row">
          <span>👁 {item.reach ?? 0}</span>
          <span>▶ {item.views ?? 0}</span>
          <span>❤ {item.engagement ?? 0}</span>
        </div>
      )}

      {item.status !== 'posted' && (
        <div className="card-actions">
          {item.status === 'draft' && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setShowScheduler((v) => !v)}
            >
              Schedule
            </button>
          )}
          {confirmPost ? (
            <>
              <span style={{ fontSize: 12, color: 'var(--muted)', alignSelf: 'center' }}>Post to Facebook?</span>
              <button className="btn btn-success btn-sm" onClick={handlePostNow} disabled={posting}>
                {posting ? 'Posting…' : 'Yes, post'}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmPost(false)}>Cancel</button>
            </>
          ) : (
            <button
              className="btn btn-success btn-sm"
              onClick={() => setConfirmPost(true)}
              disabled={posting}
            >
              {posting ? 'Posting…' : 'Post Now'}
            </button>
          )}
        </div>
      )}

      {showScheduler && (
        <div className="schedule-inline">
          <input
            type="datetime-local"
            value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)}
          />
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSchedule}
            disabled={scheduling || !scheduleTime}
          >
            {scheduling ? '…' : 'Set'}
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setShowScheduler(false)}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  )
}
