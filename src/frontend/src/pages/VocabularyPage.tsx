import { useEffect, useState } from 'react'
import { api, type UnknownTerm, type VocabularyData } from '../services/api'

const DIMENSIONS = ['products', 'solutions', 'verticals', 'platforms', 'difficulty']

export function VocabularyPage() {
  const [vocab, setVocab] = useState<VocabularyData | null>(null)
  const [terms, setTerms] = useState<UnknownTerm[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [aliasTargets, setAliasTargets] = useState<Record<string, string>>({})
  const [openDimension, setOpenDimension] = useState('products')

  const load = () => {
    setLoading(true)
    Promise.all([api.getVocabulary(), api.getVocabularyUnknowns('pending')])
      .then(([v, u]) => { setVocab(v); setTerms(u.terms) })
      .catch(() => setError('Failed to load vocabulary.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const rowKey = (t: UnknownTerm) => `${t.dimension}::${t.term}`

  const resolve = async (
    t: UnknownTerm,
    action: 'alias' | 'promote' | 'reject',
  ) => {
    const key = rowKey(t)
    if (action === 'alias' && !aliasTargets[key]) {
      setError('Pick a canonical name to alias to.')
      return
    }
    setBusy(key)
    setError('')
    try {
      await api.resolveVocabularyTerm(t.dimension, t.term, action, aliasTargets[key])
      setTerms(prev => prev.filter(x => rowKey(x) !== key))
    } catch {
      setError(`Failed to record decision for '${t.term}'.`)
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <div className="admin-layout"><div style={{ color: 'var(--text-muted)' }}>Loading…</div></div>

  return (
    <div className="admin-layout admin-layout--wide">
      {error && (
        <div style={{ color: 'var(--score-red, #c9190b)', fontSize: '12px', marginBottom: '10px' }}>
          {error}
        </div>
      )}

      <div className="admin-section">
        <h3>Pending Terms</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
          Terms analysis produced that are not in the vocabulary. The item kept the value
          verbatim — the list is what is missing an entry. Decisions are staged: they take
          effect when a regenerated <code>vocabulary.yaml</code> is committed and deployed.
        </p>

        {terms.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Queue is empty.</div>
        ) : (
          <table className="status-table">
            <thead>
              <tr>
                <th>Dimension</th><th>Term</th><th>Count</th><th>Example</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {terms.map(t => {
                const key = rowKey(t)
                const canonicals = vocab?.dimensions[t.dimension] ?? []
                return (
                  <tr key={key}>
                    <td style={{ color: 'var(--text-muted)' }}>{t.dimension}</td>
                    <td>{t.term}</td>
                    <td>{t.occurrences}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                      {t.example_content_id ?? '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <select
                          className="filter-select"
                          style={{ width: 'auto', maxWidth: '220px' }}
                          value={aliasTargets[key] ?? ''}
                          onChange={e => setAliasTargets(prev => ({ ...prev, [key]: e.target.value }))}
                        >
                          <option value="">Alias to…</option>
                          {canonicals.map(c => (
                            <option key={c.name} value={c.name}>{c.name}</option>
                          ))}
                        </select>
                        <button
                          className="action-btn action-btn--primary"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'alias')}
                        >
                          Alias
                        </button>
                        <button
                          className="action-btn"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'promote')}
                        >
                          Promote
                        </button>
                        <button
                          className="action-btn"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'reject')}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}

        <div style={{ marginTop: '16px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <a
            className="action-btn action-btn--primary"
            href={api.vocabularyGenerateUrl()}
            download="vocabulary.yaml"
          >
            Generate vocabulary.yaml
          </a>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Downloads the merged file. Commit it, open a PR, deploy.
          </span>
        </div>
      </div>

      <div className="admin-section">
        <h3>Current Vocabulary</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
          As loaded by this process — reflects any ConfigMap override in effect. Read-only;
          renaming or removing an entry is a direct edit to <code>vocabulary.yaml</code> via PR.
        </p>

        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', flexWrap: 'wrap' }}>
          {DIMENSIONS.map(d => (
            <button
              key={d}
              className={`action-btn${openDimension === d ? ' action-btn--primary' : ''}`}
              onClick={() => setOpenDimension(d)}
            >
              {d} ({vocab?.dimensions[d]?.length ?? 0})
            </button>
          ))}
        </div>

        <table className="status-table">
          <thead>
            <tr><th>Canonical name</th><th>Aliases</th><th>Search terms</th></tr>
          </thead>
          <tbody>
            {(vocab?.dimensions[openDimension] ?? []).map(e => (
              <tr key={e.name}>
                <td>
                  {e.name}
                  {e.is_tdp && (
                    <span style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--text-muted)', border: '1px solid var(--border-default)', borderRadius: '3px', padding: '1px 5px' }}>
                      TDP
                    </span>
                  )}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {e.aliases.join(', ') || '—'}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {e.search_terms.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {(vocab?.ignored_terms[openDimension]?.length ?? 0) > 0 && (
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Ignored: {vocab?.ignored_terms[openDimension].join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}
