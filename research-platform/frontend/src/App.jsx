import { useState } from 'react'

export default function App() {
  const [query, setQuery] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState('')
  const [report, setReport] = useState('')
  const [loading, setLoading] = useState(false)

  async function submitQuery() {
    setLoading(true)
    setStatus('Submitting...')
    setReport('')
    const res = await fetch('http://localhost:8000/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    })
    const { task_id } = await res.json()
    setTaskId(task_id)
    pollStatus(task_id)
  }

  function pollStatus(id) {
    const interval = setInterval(async () => {
      const res = await fetch(`http://localhost:8001/tasks/${id}`)
      const data = await res.json()
      setStatus(data.status)
      if (data.report) setReport(data.report)
      if (data.status === 'DONE' || data.status === 'FAILED') {
        clearInterval(interval)
        setLoading(false)
      }
    }, 3000)
  }

  return (
    <div style={{maxWidth: 800, margin: '40px auto', fontFamily: 'sans-serif', padding: '0 20px'}}>
      <h1>🔍 Research Platform</h1>
      <textarea
        rows={3}
        style={{width:'100%', padding: 8, fontSize: 16}}
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder='Enter your research query...'
      />
      <button
        onClick={submitQuery}
        disabled={loading || !query}
        style={{marginTop: 8, padding: '10px 24px', fontSize: 16, cursor: 'pointer'}}
      >
        {loading ? 'Researching...' : 'Run Research'}
      </button>
      {status && <p><b>Status:</b> {status}</p>}
      {report && (
        <pre style={{whiteSpace:'pre-wrap', background:'#f5f5f5', padding: 16, borderRadius: 8}}>
          {report}
        </pre>
      )}
    </div>
  )
}
