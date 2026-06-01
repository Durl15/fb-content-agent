import { useState } from 'react'
import { getReport } from '../api.js'

export default function ReportView({ toast }) {
  const [report, setReport] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleGenerate() {
    setLoading(true)
    try {
      const res = await getReport()
      setReport(res.report)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Weekly Report</div>
          <div className="section-sub">AI-generated performance summary and recommendations</div>
        </div>
        <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
          {loading ? (
            <>
              <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              Generating…
            </>
          ) : (
            'Generate Report'
          )}
        </button>
      </div>

      {!report && !loading && (
        <div className="empty">
          <div className="empty-icon">📝</div>
          <p>Click Generate Report to get AI-powered insights on your content performance.</p>
        </div>
      )}

      {report && (
        <div className="report-box">{report}</div>
      )}
    </>
  )
}
