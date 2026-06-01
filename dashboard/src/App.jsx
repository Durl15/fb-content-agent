import { useState, useCallback } from 'react'
import ContentList from './components/ContentList.jsx'
import PerformanceView from './components/PerformanceView.jsx'
import ReportView from './components/ReportView.jsx'
import TokenBanner from './components/TokenBanner.jsx'

const TABS = ['content', 'performance', 'report']

export default function App() {
  const [tab, setTab] = useState('content')
  const [toasts, setToasts] = useState([])

  const toast = useCallback((msg, type = 'success') => {
    const id = Date.now()
    setToasts((t) => [...t, { id, msg, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500)
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-title">FB <span>Content</span> Agent</div>
        <nav className="nav">
          {TABS.map((t) => (
            <button
              key={t}
              className={`nav-btn ${tab === t ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
      </header>

      <TokenBanner />
      <main className="main">
        {tab === 'content' && <ContentList toast={toast} />}
        {tab === 'performance' && <PerformanceView toast={toast} />}
        {tab === 'report' && <ReportView toast={toast} />}
      </main>

      <div className="toast-container">
        {toasts.map(({ id, msg, type }) => (
          <div key={id} className={`toast toast-${type}`}>{msg}</div>
        ))}
      </div>
    </div>
  )
}
