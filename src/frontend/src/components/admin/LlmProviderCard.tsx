// LLM Provider status card (RHDPCD-2226).
// LiteMaaS is the only provider. The former Vertex/Anthropic fallback was
// removed on 2026-11-03; if a fallback is ever needed it will be built then.

export interface LlmUse {
  use: string
  model: string
}

export interface LlmProviderStatus {
  litemaas_enabled: boolean
  litemaas_url: string | null
  litemaas_models: string[]
  uses: LlmUse[]
}

const USE_LABELS: Record<string, string> = {
  analysis: 'Analysis',
  triage: 'Triage',
  rationale: 'Rationale',
  scanning: 'Scanning',
  chat_router: 'Chat Router',
  chat_answer: 'Chat Answer',
  overlap: 'Overlap',
  osspa_analysis: 'OSSPA Analysis',
}

export function LlmProviderCard({ status }: { status: LlmProviderStatus }) {
  return (
    <>
      <div className="admin-stat-row">
        <span className="admin-stat-row-label">Active</span>
        <span style={{ color: status.litemaas_enabled ? 'var(--score-green)' : 'var(--text-muted)' }}>
          {status.litemaas_enabled ? 'LiteMaaS' : 'None'}
        </span>
      </div>
      {status.litemaas_enabled && status.litemaas_models.length > 0 && (
        <div className="admin-stat-row">
          <span className="admin-stat-row-indent">Models</span>
          <span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{status.litemaas_models.join(', ')}</span>
        </div>
      )}
      <div className="admin-stat-row-divider" />
      {status.uses.map(({ use, model }) => (
        <div className="admin-stat-row" key={use}>
          <span className="admin-stat-row-label">{USE_LABELS[use] ?? use}</span>
          <span className="admin-stat-row-value" style={{ fontSize: '11px' }}>{model}</span>
        </div>
      ))}
    </>
  )
}
