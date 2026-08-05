import { describe, expect, it } from 'vitest'
import { resolveBlockRenderer } from './registry'
import { UnknownBlock } from './UnknownBlock'
import { RecCardsBlock } from './RecCardsBlock'

describe('block renderer registry', () => {
  it('dispatches known block types', () => {
    expect(resolveBlockRenderer('rec_cards')).toBe(RecCardsBlock)
    for (const t of ['overlap_table', 'performance_table', 'item_card', 'notice']) {
      expect(resolveBlockRenderer(t)).not.toBe(UnknownBlock)
    }
  })

  it('falls back for unknown block types', () => {
    expect(resolveBlockRenderer('portfolio_gaps')).toBe(UnknownBlock)
    expect(resolveBlockRenderer('')).toBe(UnknownBlock)
  })
})
