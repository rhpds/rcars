import { useState, useCallback } from 'react'
import { api } from '../services/api'

// ── Interfaces ──

interface WorkloadMapping {
  workload_role: string
  product_name: string
  description: string | null
  category: string | null
  verified: boolean
}

interface UnmappedWorkload {
  workload_role: string
  workload_collection: string | null
  ci_count: number
}

// ── WorkloadsPage ──

export function WorkloadsPage() {
  const [mappings, setMappings] = useState<WorkloadMapping[]>([])
  const [unmapped, setUnmapped] = useState<UnmappedWorkload[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [mappingForm, setMappingForm] = useState<Record<string, { product: string; category: string }>>({})

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [mapData, unmapData] = await Promise.all([
        api.getWorkloadMappings() as Promise<{ mappings: WorkloadMapping[]; aliases: unknown[] }>,
        api.getUnmappedWorkloads() as Promise<{ unmapped: UnmappedWorkload[] }>,
      ])
      setMappings(mapData.mappings.sort((a, b) => a.product_name.localeCompare(b.product_name)))
      setUnmapped(unmapData.unmapped.sort((a, b) => b.ci_count - a.ci_count))
      setLoaded(true)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  // Load data on first render
  if (!loaded && !loading) {
    loadData()
  }

  const handleDelete = async (role: string) => {
    await api.deleteWorkloadMapping(role)
    loadData()
  }

  const handleMap = async (role: string) => {
    const form = mappingForm[role]
    if (!form?.product?.trim()) return
    await api.addWorkloadMapping({
      workload_role: role,
      product_name: form.product.trim(),
      category: form.category?.trim() || undefined,
    })
    setMappingForm(prev => { const next = { ...prev }; delete next[role]; return next })
    loadData()
  }

  if (loading && !loaded) {
    return (
      <div className="admin-layout admin-layout--wide">
        <div style={{ color: 'var(--text-muted)' }}>Loading workload mappings...</div>
      </div>
    )
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <h3>
          Workload Mappings
          {mappings.length > 0 && (
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'normal', textTransform: 'none', letterSpacing: 0, marginLeft: '8px' }}>
              {mappings.length} mapped &middot; {unmapped.length} unmapped
            </span>
          )}
        </h3>

        {unmapped.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', color: 'var(--score-amber)', marginBottom: '8px', fontWeight: 600 }}>
              Unmapped Workloads ({unmapped.length})
            </div>
            <table className="status-table status-table--compact">
              <thead><tr><th>Role</th><th>Collection</th><th style={{ textAlign: 'right' }}>CIs</th><th></th></tr></thead>
              <tbody>
                {unmapped.map(u => (
                  <tr key={u.workload_role}>
                    <td style={{ fontFamily: 'var(--ff-mono)', fontSize: '11px' }}>{u.workload_role}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{u.workload_collection || '—'}</td>
                    <td style={{ textAlign: 'right' }}>{u.ci_count}</td>
                    <td style={{ textAlign: 'right' }}>
                      {mappingForm[u.workload_role] !== undefined ? (
                        <div className="mapping-inline-form">
                          <input
                            placeholder="Product name"
                            value={mappingForm[u.workload_role]?.product || ''}
                            onChange={(e) => setMappingForm(prev => ({
                              ...prev, [u.workload_role]: { ...prev[u.workload_role], product: e.target.value }
                            }))}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                          />
                          <input
                            placeholder="Category"
                            value={mappingForm[u.workload_role]?.category || ''}
                            onChange={(e) => setMappingForm(prev => ({
                              ...prev, [u.workload_role]: { ...prev[u.workload_role], category: e.target.value }
                            }))}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleMap(u.workload_role) }}
                            style={{ width: '100px' }}
                          />
                          <button onClick={() => handleMap(u.workload_role)}>Save</button>
                          <button
                            onClick={() => setMappingForm(prev => { const next = { ...prev }; delete next[u.workload_role]; return next })}
                            style={{ background: 'none', color: 'var(--text-muted)' }}
                          >&#10005;</button>
                        </div>
                      ) : (
                        <button
                          className="mapping-delete-btn"
                          style={{ color: 'var(--text-link)' }}
                          onClick={() => setMappingForm(prev => ({ ...prev, [u.workload_role]: { product: '', category: '' } }))}
                        >
                          Map
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div>
          <div style={{ fontSize: '13px', color: 'var(--score-green)', marginBottom: '8px', fontWeight: 600 }}>
            Mapped Workloads ({mappings.length})
          </div>
          <table className="status-table status-table--compact">
            <thead><tr><th>Role</th><th>Product Name</th><th>Category</th><th></th><th></th></tr></thead>
            <tbody>
              {mappings.map(m => (
                <tr key={m.workload_role}>
                  <td style={{ fontFamily: 'var(--ff-mono)', fontSize: '11px' }}>{m.workload_role}</td>
                  <td>{m.product_name}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{m.category || '—'}</td>
                  <td>{m.verified && <span className="verified-badge">verified</span>}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="mapping-delete-btn" onClick={() => handleDelete(m.workload_role)} title="Remove mapping">&#10005;</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
