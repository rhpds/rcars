import type { ComponentType } from 'react'
import type { ChatBlock } from '../chatTypes'
import { RecCardsBlock } from './RecCardsBlock'
import { OverlapTableBlock } from './OverlapTableBlock'
import { PerformanceTableBlock } from './PerformanceTableBlock'
import { ItemCardBlock } from './ItemCardBlock'
import { NoticeBlock } from './NoticeBlock'
import { UnknownBlock } from './UnknownBlock'

export interface BlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

const RENDERERS: Record<string, ComponentType<BlockProps>> = {
  rec_cards: RecCardsBlock,
  overlap_table: OverlapTableBlock,
  performance_table: PerformanceTableBlock,
  item_card: ItemCardBlock,
  notice: NoticeBlock,
}

export function resolveBlockRenderer(type: string): ComponentType<BlockProps> {
  return RENDERERS[type] ?? UnknownBlock
}
