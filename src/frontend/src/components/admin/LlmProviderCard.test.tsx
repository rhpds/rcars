import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { LlmProviderCard, type LlmProviderStatus } from './LlmProviderCard'

const status: LlmProviderStatus = {
  litemaas_enabled: true,
  litemaas_url: 'https://maas.example.com/v1',
  litemaas_models: ['claude-haiku-5-5-a8b', 'claude-sonnet-5-5-a46b'],
  fallback_enabled: false,
  uses: [
    { use: 'analysis', model: 'claude-sonnet-5-5-a46b' },
    { use: 'triage', model: 'claude-haiku-5-5-a8b' },
    { use: 'chat_router', model: 'claude-haiku-5-5-a8b' },
    { use: 'osspa_analysis', model: 'claude-sonnet-5-5-a46b' },
  ],
}

describe('LlmProviderCard', () => {
  it('shows LiteMaaS as the active provider with its models', () => {
    const html = renderToStaticMarkup(<LlmProviderCard status={status} />)
    expect(html).toContain('Active')
    expect(html).toContain('LiteMaaS')
    expect(html).toContain('claude-sonnet-5-5-a46b')
    expect(html).toContain('claude-haiku-5-5-a8b')
  })

  it('shows the fallback as not active when dormant', () => {
    const html = renderToStaticMarkup(<LlmProviderCard status={status} />)
    expect(html).toContain('Fallback')
    expect(html).toContain('Not active')
    expect(html).not.toContain('Vertex AI')
  })

  it('shows the fallback provider name when it is enabled', () => {
    const html = renderToStaticMarkup(
      <LlmProviderCard status={{ ...status, fallback_enabled: true }} />,
    )
    expect(html).toContain('Vertex AI')
    expect(html).not.toContain('Not active')
  })

  it('lists the model for every LLM use with readable labels', () => {
    const html = renderToStaticMarkup(<LlmProviderCard status={status} />)
    expect(html).toContain('Analysis')
    expect(html).toContain('Triage')
    expect(html).toContain('Chat Router')
    expect(html).toContain('OSSPA Analysis')
  })

  it('falls back to the raw use key for unknown uses', () => {
    const html = renderToStaticMarkup(
      <LlmProviderCard status={{ ...status, uses: [{ use: 'new_thing', model: 'm' }] }} />,
    )
    expect(html).toContain('new_thing')
  })
})
