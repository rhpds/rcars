import { useState, useEffect, useCallback } from 'react'
import { api } from '../../services/api'

interface ApiKeyRow {
  id: number
  key_prefix: string
  name: string
  created_by: string
  role: string
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  is_active: boolean
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function expiryLabel(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours}h left`
  const days = Math.floor(hours / 24)
  return `${days}d left`
}

export function ApiKeysPanel() {
  const [keys, setKeys] = useState<ApiKeyRow[]>([])
  const [showAll, setShowAll] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyRole, setNewKeyRole] = useState('user')
  const [newKeyExpiry, setNewKeyExpiry] = useState<string>('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [revokeConfirm, setRevokeConfirm] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchKeys = useCallback(() => {
    api.listApiKeys(!showAll)
      .then(data => setKeys(data.keys))
      .catch(e => setError(e.message))
  }, [showAll])

  useEffect(() => { fetchKeys() }, [fetchKeys])

  const handleCreate = async () => {
    try {
      const expiresInDays = newKeyExpiry ? parseInt(newKeyExpiry) : null
      const result = await api.createApiKey(newKeyName, newKeyRole, expiresInDays)
      setCreatedKey(result.api_key)
      setShowCreate(false)
      setNewKeyName('')
      setNewKeyRole('user')
      setNewKeyExpiry('')
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    }
  }

  const handleRevoke = async (keyId: number) => {
    try {
      await api.revokeApiKey(keyId)
      setRevokeConfirm(null)
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3>API Keys</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <input type="checkbox" checked={showAll} onChange={() => setShowAll(!showAll)} />
              Show revoked/expired
            </label>
            <button className="action-button" onClick={() => setShowCreate(true)}>Create Key</button>
          </div>
        </div>

        {error && (
          <div style={{ color: 'var(--score-red)', marginBottom: '8px', fontSize: '13px' }}>
            {error}
            <button onClick={() => setError(null)} style={{ marginLeft: '8px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>dismiss</button>
          </div>
        )}

        {createdKey && (
          <div style={{
            background: 'var(--status-bg-warning)',
            border: '1px solid var(--score-amber)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '12px',
            fontSize: '13px',
          }}>
            <strong>API key created — copy it now, it won't be shown again:</strong>
            <div style={{ fontFamily: 'monospace', marginTop: '6px', wordBreak: 'break-all', userSelect: 'all' }}>
              {createdKey}
            </div>
            <button
              className="action-button"
              style={{ marginTop: '8px' }}
              onClick={() => { navigator.clipboard.writeText(createdKey); setCreatedKey(null) }}
            >
              Copy & Dismiss
            </button>
          </div>
        )}

        {showCreate && (
          <div style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '12px',
          }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <input
                placeholder="Key name (e.g. Babylon integration)"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                style={{ flex: 1, minWidth: '200px' }}
                className="filter-input"
              />
              <select className="filter-select" value={newKeyRole} onChange={e => setNewKeyRole(e.target.value)}>
                <option value="user">user</option>
                <option value="curator">curator</option>
                <option value="admin">admin</option>
              </select>
              <select className="filter-select" value={newKeyExpiry} onChange={e => setNewKeyExpiry(e.target.value)}>
                <option value="">Never expires</option>
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="action-button" onClick={handleCreate} disabled={!newKeyName.trim()}>Create</button>
              <button className="action-button" onClick={() => setShowCreate(false)} style={{ background: 'transparent', color: 'var(--text-muted)' }}>Cancel</button>
            </div>
          </div>
        )}

        {keys.length > 0 ? (
          <table className="status-table">
            <thead>
              <tr>
                <th>Prefix</th>
                <th>Name</th>
                <th>Created by</th>
                <th>Role</th>
                <th>Created</th>
                <th>Expires</th>
                <th>Last used</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <tr key={k.id} style={{ opacity: k.is_active ? 1 : 0.5 }}>
                  <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{k.key_prefix}...</td>
                  <td>{k.name}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{k.created_by}</td>
                  <td>{k.role}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{timeAgo(k.created_at)}</td>
                  <td>{expiryLabel(k.expires_at)}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{timeAgo(k.last_used_at)}</td>
                  <td>
                    <span style={{
                      color: k.is_active ? 'var(--score-green)' : 'var(--score-red)',
                      fontSize: '12px',
                    }}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td>
                    {k.is_active && (
                      revokeConfirm === k.id ? (
                        <span style={{ fontSize: '12px' }}>
                          Revoke?{' '}
                          <button onClick={() => handleRevoke(k.id)} style={{ color: 'var(--score-red)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Yes</button>
                          {' / '}
                          <button onClick={() => setRevokeConfirm(null)} style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>No</button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setRevokeConfirm(k.id)}
                          style={{ color: 'var(--score-red)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: '12px' }}
                        >
                          Revoke
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: 'var(--text-muted)' }}>No API keys found.</div>
        )}
      </div>
    </div>
  )
}
