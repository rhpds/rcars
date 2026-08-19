import { useState } from 'react'
import type { ChatBlock } from '../chatTypes'

interface InfraDetailBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

const ITEMS_PREVIEW = 5

export function InfraDetailBlock({ block }: InfraDetailBlockProps) {
  const [showAllItems, setShowAllItems] = useState(false)
  const d = block.data
  const roleName = d.role_name as string
  const type = d.type as string
  const description = d.description as string | null
  const products = (d.products || []) as string[]
  const capabilities = (d.capabilities || []) as string[]
  const category = d.category as string | null
  const requires = (d.requires || []) as string[]
  const collection = d.collection as string | null
  const items = (d.items || []) as Array<{ display_name: string; ci_name?: string; stage?: string }>
  const others = (d.other_matches || []) as Array<{ role_name: string; type: string; description: string; products: string[] }>
  const secondary = d.secondary as { role_name: string; type: string; description?: string; products?: string[]; capabilities?: string[]; category?: string; requires?: string[]; collection?: string; item_count?: number } | undefined

  const label = { fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' as const, marginBottom: '4px' }
  const pill = { padding: '2px 6px', borderRadius: '3px', fontSize: '11px', background: 'var(--bg-subtle)', color: 'var(--text-secondary)' }

  return (
    <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px', background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, flex: 1 }}>
          <a href={`/browse/workloads?search=${encodeURIComponent(roleName)}`}
             target="_blank" rel="noopener noreferrer"
             style={{ color: 'inherit', textDecoration: 'none' }}>
            {roleName}
          </a>
        </h3>
        <span style={{ ...pill, background: type === 'config' ? 'var(--badge-amber-bg)' : 'var(--badge-blue-bg)',
                       color: type === 'config' ? 'var(--badge-amber-text)' : 'var(--badge-blue-text)' }}>{type}</span>
        {category && <span style={pill}>{category}</span>}
      </div>

      {description && <p style={{ margin: '0 0 12px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>{description}</p>}

      {products.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={label}>Products</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {products.map((p, i) => <span key={i} style={pill}>{p}</span>)}
          </div>
        </div>
      )}

      {capabilities.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={label}>Capabilities</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {capabilities.map((c, i) => <span key={i} style={pill}>{c}</span>)}
          </div>
        </div>
      )}

      {requires.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={label}>Requires</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{requires.join(', ')}</div>
        </div>
      )}

      {collection && (
        <div style={{ marginBottom: '12px' }}>
          <div style={label}>Collection</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{collection}</div>
        </div>
      )}

      {items.length > 0 && (() => {
        const grouped = new Map<string, { name: string; stages: string[] }>()
        for (const ci of items) {
          const name = ci.display_name || ci.ci_name || ''
          const entry = grouped.get(name)
          if (entry) { if (ci.stage && !entry.stages.includes(ci.stage)) entry.stages.push(ci.stage) }
          else grouped.set(name, { name, stages: ci.stage ? [ci.stage] : [] })
        }
        const all = [...grouped.values()]
        const visible = showAllItems ? all : all.slice(0, ITEMS_PREVIEW)
        return (
          <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', marginBottom: others.length > 0 ? '12px' : 0 }}>
            <div style={label}>Used by {grouped.size} catalog item{grouped.size !== 1 ? 's' : ''}</div>
            {visible.map((g, i) => {
              const extraStages = g.stages.filter(s => s !== 'prod').join(',')
              const href = `/browse?search=${encodeURIComponent(g.name)}${extraStages ? `&stage=${extraStages}` : ''}`
              return (
                <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <a href={href} target="_blank" rel="noopener noreferrer"
                     style={{ color: 'var(--text-link)', textDecoration: 'none' }}>{g.name}</a>
                  {g.stages.filter(s => s !== 'prod').map(s => <span key={s} style={{ ...pill, fontSize: '10px' }}>{s}</span>)}
                </div>
              )
            })}
            {all.length > ITEMS_PREVIEW && (
              <button
                onClick={() => setShowAllItems(v => !v)}
                style={{ marginTop: '4px', background: 'none', border: 'none', padding: 0, fontSize: '12px', color: 'var(--text-link)', cursor: 'pointer' }}
              >
                {showAllItems ? 'Show fewer' : `Show all ${all.length} items`}
              </button>
            )}
          </div>
        )
      })()}

      {secondary && (
        <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
          <div style={label}>Also relevant ({secondary.type})</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <a href={`/browse/workloads?search=${encodeURIComponent(secondary.role_name)}`}
               target="_blank" rel="noopener noreferrer"
               style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-link)', textDecoration: 'none' }}>
              {secondary.role_name}
            </a>
            <span style={{ ...pill, background: secondary.type === 'config' ? 'var(--badge-amber-bg)' : 'var(--badge-blue-bg)',
                           color: secondary.type === 'config' ? 'var(--badge-amber-text)' : 'var(--badge-blue-text)' }}>
              {secondary.type}
            </span>
          </div>
          {secondary.description && (
            <p style={{ margin: '0 0 6px', fontSize: '12px', color: 'var(--text-secondary)' }}>{secondary.description}</p>
          )}
          {secondary.item_count != null && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Used by {secondary.item_count} catalog item{secondary.item_count !== 1 ? 's' : ''}</div>
          )}
        </div>
      )}

      {others.length > 0 && (
        <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={label}>Other matches</div>
          {others.map((o, i) => (
            <div key={i} style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '2px' }}>
              <a href={`/browse/workloads?search=${encodeURIComponent(o.role_name)}`}
                 target="_blank" rel="noopener noreferrer"
                 style={{ color: 'var(--text-link)', textDecoration: 'none', fontWeight: 600 }}>
                {o.role_name}
              </a>
              {' '}({o.type}) — {o.description || o.products.join(', ') || 'no description'}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
