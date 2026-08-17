import type { ChatBlock } from '../chatTypes'

interface InfraDetailBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

export function InfraDetailBlock({ block }: InfraDetailBlockProps) {
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

  const label = { fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' as const, marginBottom: '4px' }
  const pill = { padding: '2px 6px', borderRadius: '3px', fontSize: '11px', background: 'var(--bg-subtle)', color: 'var(--text-secondary)' }

  return (
    <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '16px', background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, flex: 1 }}>{roleName}</h3>
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
        return (
          <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', marginBottom: others.length > 0 ? '12px' : 0 }}>
            <div style={label}>Used by {grouped.size} catalog item{grouped.size !== 1 ? 's' : ''}</div>
            {[...grouped.values()].map((g, i) => (
              <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                {g.stages.map(s => <span key={s} style={{ ...pill, fontSize: '10px' }}>{s}</span>)}
                <a href={`/browse?search=${encodeURIComponent(g.name)}`}
                   style={{ color: 'var(--text-link)', textDecoration: 'none' }}>{g.name}</a>
              </div>
            ))}
          </div>
        )
      })()}

      {others.length > 0 && (
        <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={label}>Other matches</div>
          {others.map((o, i) => (
            <div key={i} style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '2px' }}>
              <strong>{o.role_name}</strong> ({o.type}) — {o.description || o.products.join(', ') || 'no description'}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
