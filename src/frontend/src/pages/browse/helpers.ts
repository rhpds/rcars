/* Pure helpers for the Browse page. Kept out of BrowsePage.tsx so they are
   unit-testable without a DOM testing library. */

export type ContentFormat = 'hands_on' | 'architecture'

export const HANDS_ON_TYPES = ['lab', 'demo', 'sandbox'] as const

export interface KeyableItem {
  content_id?: string | null
  ci_name?: string | null
}

/** Map the selected formats to the API's content_type param.
 *  Always explicit, never omitted: a future content type must not slip into
 *  the default view just because nobody listed it. */
export function contentTypeParam(formats: Set<ContentFormat>): string {
  const types: string[] = []
  if (formats.size === 0 || formats.has('hands_on')) types.push(...HANDS_ON_TYPES)
  if (formats.has('architecture')) types.push('architecture')
  return types.join(',')
}

/** content_id is present on every row, Babylon included; ci_name is not. */
export function itemKey(item: KeyableItem): string {
  return item.content_id || item.ci_name || ''
}

export function isZtItem(item: { catalog_namespace?: string | null; ci_name?: string | null }): boolean {
  return Boolean(item.catalog_namespace?.startsWith('zt-')) || Boolean(item.ci_name?.startsWith('zt-'))
}

export function isArchitecture(item: { source?: string | null }): boolean {
  return item.source === 'portfolio_arch'
}

/* Never "Reference Architecture": a reference architecture is a prescriptive
   Red Hat artifact, and these are curated "art of the possible" examples.
   Mislabelling them sets a false expectation for sales teams. */
const ASSET_TYPE_LABELS: Record<string, string> = {
  VP: 'Validated Pattern',
  SP: 'Solution Pattern',
  PA: 'Portfolio Architecture',
}

export function assetTypeLabel(assetType?: string | null): string {
  const tokens = (assetType || '').split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
  for (const candidate of ['VP', 'SP', 'PA']) {
    if (tokens.includes(candidate)) return ASSET_TYPE_LABELS[candidate]
  }
  return 'Architecture'
}

export function architectureDetailUrl(paName?: string | null): string {
  return paName ? `https://www.redhat.com/architect/portfolio/detail/${paName}/` : '#'
}

export function architectureSubline(
  item: { pa_name?: string | null; solutions?: string[] | null },
): string {
  const primary = item.solutions?.[0] || 'Architecture'
  return `${item.pa_name || ''} · ${primary}`
}
