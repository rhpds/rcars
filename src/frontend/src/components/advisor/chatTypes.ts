export interface ChatChip {
  label: string
  intent: string
  args: Record<string, unknown>
  scope: Record<string, unknown> | null
}

export interface ChatBlock {
  type: string
  data: Record<string, unknown>
}

export interface ChatEnvelope {
  intent: string
  scope_echo: string
  answer: string
  blocks: ChatBlock[]
  suggested_followups: ChatChip[]
  session_id?: string
}
