export const NONE_LABEL = '__none__'

/**
 * Display a label value for UI rendering.
 * Converts NONE_LABEL to 'None', otherwise replaces underscores with spaces.
 */
export function labelDisplay(value: string): string {
  if (value === NONE_LABEL) {
    return 'None'
  }
  return value.replace(/_/g, ' ')
}

/**
 * Check if an item's label values match the selected filter set.
 * Returns true if:
 * - selected is empty (no filter applied), OR
 * - any value is in selected, OR
 * - values is empty AND NONE_LABEL is in selected
 */
export function matchesLabels(values: string[], selected: Set<string>): boolean {
  if (selected.size === 0) {
    return true
  }

  if (values.length === 0) {
    return selected.has(NONE_LABEL)
  }

  return values.some(v => selected.has(v))
}

/**
 * Count label values across items. Each value is counted once per item.
 * Items with no values count under NONE_LABEL.
 * Returns [label, count][] sorted by count desc, then name asc.
 * NONE_LABEL is always last when present.
 */
export function countLabelValues<T>(items: T[], get: (i: T) => string[]): [string, number][] {
  const counts = new Map<string, number>()

  for (const item of items) {
    const values = get(item)
    if (values.length === 0) {
      counts.set(NONE_LABEL, (counts.get(NONE_LABEL) || 0) + 1)
    } else {
      for (const value of values) {
        counts.set(value, (counts.get(value) || 0) + 1)
      }
    }
  }

  const entries = Array.from(counts.entries())

  // Separate NONE_LABEL from others
  const noneEntry = entries.find(([label]) => label === NONE_LABEL)
  const otherEntries = entries.filter(([label]) => label !== NONE_LABEL)

  // Sort others by count desc, then name asc
  otherEntries.sort((a, b) => {
    if (b[1] !== a[1]) {
      return b[1] - a[1]
    }
    return a[0].localeCompare(b[0])
  })

  // Append NONE_LABEL at the end if present
  if (noneEntry) {
    otherEntries.push(noneEntry)
  }

  return otherEntries
}

/**
 * Items that pass every filter except the one named `skip`.
 * Feed this to a filter group's counts, so each count shows how many items
 * that option would give with the other active filters applied.
 */
export function applyFilters<T>(items: T[], filters: Record<string, (i: T) => boolean>, skip?: string): T[] {
  const active = Object.entries(filters).filter(([key]) => key !== skip).map(([, f]) => f)
  return items.filter(i => active.every(f => f(i)))
}

/**
 * Add selected values that have no count to the end of an option list, with a count of 0,
 * so a checked box never disappears when other filters remove all of its items.
 */
export function withSelected(options: [string, number?][], selected: Set<string>): [string, number?][] {
  const present = new Set(options.map(([value]) => value))
  const missing = [...selected].filter(v => !present.has(v)).sort().map(v => [v, 0] as [string, number])
  return [...options, ...missing]
}
