import type { ChatBlock } from '../chatTypes'

interface ItemCardBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

interface ItemNeighbor {
  display_name: string
  similarity_pct: number
}

function catalogUrl(ciName: string, namespace: string): string {
  const ns = namespace || 'babylon-catalog-prod'
  return `https://demo.redhat.com/catalog?item=${ns}/${ciName}`
}

export function ItemCardBlock({ block }: ItemCardBlockProps) {
  const displayName = block.data.display_name as string | undefined
  const ciName = block.data.ci_name as string | undefined
  const namespace = block.data.catalog_namespace as string | undefined
  const stage = block.data.stage as string | undefined
  const contentType = block.data.content_type as string | undefined
  const summary = block.data.summary as string | undefined
  const products = (block.data.products || []) as string[]
  const modules = (block.data.modules || []) as string[]
  const workloads = (block.data.workloads || []) as string[]
  const neighbors = (block.data.neighbors || []) as ItemNeighbor[]

  if (!displayName) return null

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-sm)',
      padding: '16px',
      background: 'var(--bg-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, flex: 1 }}>
          {displayName}
        </h3>
        {stage && stage !== 'prod' && (
          <span style={{
            padding: '2px 6px',
            borderRadius: '3px',
            fontSize: '11px',
            background: stage === 'dev' ? 'var(--badge-blue-bg)' : 'var(--badge-amber-bg)',
            color: stage === 'dev' ? 'var(--badge-blue-text)' : 'var(--badge-amber-text)',
          }}>
            {stage.toUpperCase()}
          </span>
        )}
        {contentType && (
          <span style={{
            padding: '2px 6px',
            borderRadius: '3px',
            fontSize: '11px',
            background: 'var(--badge-blue-bg)',
            color: 'var(--badge-blue-text)',
          }}>
            {contentType}
          </span>
        )}
      </div>

      {summary && (
        <p style={{ margin: '0 0 12px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          {summary}
        </p>
      )}

      {products.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
            Products
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {products.map((p, i) => (
              <span key={i} style={{
                padding: '2px 6px',
                borderRadius: '3px',
                fontSize: '11px',
                background: 'var(--bg-subtle)',
                color: 'var(--text-secondary)',
              }}>
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {modules.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
            Modules ({modules.length})
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {modules.slice(0, 3).join(', ')}
            {modules.length > 3 && ` +${modules.length - 3} more`}
          </div>
        </div>
      )}

      {workloads.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
            Workloads
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {workloads.join(', ')}
          </div>
        </div>
      )}

      {neighbors.length > 0 && (
        <div style={{ marginBottom: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Similar items
          </div>
          {neighbors.map((n, i) => (
            <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
              {n.display_name} ({n.similarity_pct}%)
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', fontSize: '12px' }}>
        {ciName && namespace && (
          <a
            href={catalogUrl(ciName, namespace)}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--text-link)' }}
          >
            View in RHDP Catalog
          </a>
        )}
        <a
          href={'/browse?search=' + encodeURIComponent(displayName)}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--text-link)' }}
        >
          View in RCARS
        </a>
      </div>
    </div>
  )
}
